param(
  [string]$BackendUrl = "http://localhost:8000/api/v1",
  [string]$WorkspacePath = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$packagePath = Join-Path $root "package.json"

function Write-Step {
  param([string]$Message)
  Write-Host "[RepoAlign smoke] $Message"
}

function Assert-Command {
  param(
    [object[]]$Commands,
    [string]$Command
  )

  if (-not ($Commands | Where-Object { $_.command -eq $Command })) {
    throw "Missing VS Code command registration: $Command"
  }
}

function Invoke-Json {
  param(
    [string]$Method,
    [string]$Uri,
    [object]$Body = $null
  )

  $params = @{
    Method = $Method
    Uri = $Uri
    TimeoutSec = 30
  }

  if ($null -ne $Body) {
    $params.Body = ($Body | ConvertTo-Json -Depth 10)
    $params.ContentType = "application/json"
  }

  Invoke-RestMethod @params
}

Write-Step "Checking extension manifest"
$package = Get-Content $packagePath -Raw | ConvertFrom-Json
$commands = @($package.contributes.commands)

@(
  "repoalign.showWelcome",
  "repoalign.validateWorkspace",
  "repoalign.checkReadiness",
  "repoalign.analyzeWorkspace",
  "repoalign.showIndexingStatus",
  "repoalign.rebuildGraph",
  "repoalign.resetWorkspaceIndex",
  "repoalign.reindexEmbeddings",
  "repoalign.inspectStagedChanges",
  "repoalign.analyzeStagedChanges",
  "repoalign.commitWithAnalysis",
  "repoalign.installPreCommitHook",
  "repoalign.removePreCommitHook",
  "repoalign.ignoreFindingOnce",
  "repoalign.ignoreFindingPattern",
  "repoalign.clearIgnoredFindings",
  "repoalign.generatePatch"
) | ForEach-Object { Assert-Command -Commands $commands -Command $_ }

Write-Step "Checking backend readiness at $BackendUrl"
$readiness = Invoke-Json -Method Get -Uri "$BackendUrl/readiness"
if (-not $readiness.ready) {
  $readiness | ConvertTo-Json -Depth 10
  throw "Backend readiness failed"
}

Write-Step "Checking graph status endpoint"
$graphStatus = Invoke-Json -Method Get -Uri "$BackendUrl/graph-update-status"
if ($graphStatus.status -ne "ok") {
  $graphStatus | ConvertTo-Json -Depth 10
  throw "Graph status endpoint did not return ok"
}

if ($WorkspacePath) {
  Write-Step "Checking workspace path $WorkspacePath"
  if (-not (Test-Path $WorkspacePath)) {
    throw "Workspace path does not exist: $WorkspacePath"
  }

  if (-not (Test-Path (Join-Path $WorkspacePath ".git"))) {
    throw "Workspace is not a Git repository: $WorkspacePath"
  }

  $pythonFiles = Get-ChildItem -Path $WorkspacePath -Recurse -Filter *.py -File |
    Where-Object {
      $_.FullName -notmatch "\\(\.git|\.venv|venv|__pycache__|node_modules|dist|build|htmlcov)\\"
    }

  if ($pythonFiles.Count -eq 0) {
    throw "Workspace contains no Python files after production exclusions"
  }

  Write-Step "Workspace contains $($pythonFiles.Count) Python file(s)"
}

Write-Step "Smoke test passed"
