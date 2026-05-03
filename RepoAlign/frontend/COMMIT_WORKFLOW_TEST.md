# RepoAlign Commit-Time Workflow Test

This verifies Sub-phases 10.6 through 10.10 without changing normal Git push behavior.

## Safe Commit Command Demo

1. Start the RepoAlign backend.
2. Open a Python Git repository in the Extension Development Host.
3. Edit a Python function and save it.
4. Stage the file from VS Code Source Control or with `git add`.
5. Run `RepoAlign: Analyze Staged Changes`.
6. Confirm the `RepoAlign` output channel shows:
   - recommendation
   - staged files
   - changed symbol count
   - findings
7. Run `RepoAlign: Commit With Analysis`.
8. Enter a commit message.
9. Expected: if recommendation is `ready`, Git commit completes and output records a successful analysis event.

## Blocking Demo

1. Create a staged Python syntax error.
2. Run `RepoAlign: Commit With Analysis`.
3. Expected: commit is blocked, the output channel shows a `blocker` finding, and the staged files remain staged.
4. Fix the syntax error.
5. Stage the fixed file.
6. Run `RepoAlign: Commit With Analysis` again.
7. Expected: commit completes.

## Optional Hook Demo

1. Run `RepoAlign: Install Pre-Commit Hook`.
2. Confirm `.git/hooks/pre-commit` contains `RepoAlign managed pre-commit hook`.
3. Stage a clean Python change.
4. Run `git commit -m "demo clean commit"`.
5. Expected: hook analysis prints a recommendation and allows the commit.
6. Stage a syntax error.
7. Run `git commit -m "demo blocked commit"`.
8. Expected: hook blocks the commit.
9. Run `git commit --no-verify -m "demo bypass"` only if you need to demonstrate bypass.
10. Run `RepoAlign: Remove Pre-Commit Hook`.
11. Expected: the RepoAlign-managed hook is removed.

## Push Safety Check

After a successful commit, run:

```powershell
git push
```

Expected: RepoAlign does not intercept or block push.


Here is the step-by-step test for Phase 10.1 to 10.5.

1. Start Backend
From your normal backend setup, start FastAPI, Neo4j, Qdrant, and Ollama.

Then open:

http://localhost:8000/docs#/
Check that this endpoint exists:

POST /api/v1/analyze-staged-changes
Also test readiness:

GET /api/v1/readiness
Expected: backend is ready.

2. Launch Extension Debugger
In VS Code:

Open RepoAlign/frontend.
Press F5.
A new Extension Development Host window opens.
In that new window, open your Python test project/repo.
Important: test in a real Git repo with Python files.

3. Confirm No Staged Changes Case
In the Extension Development Host:

Ctrl + Shift + P
RepoAlign: Inspect Staged Changes
Expected if nothing is staged:

Message says no staged changes found.
RepoAlign output channel opens.
Git push/commit flow is untouched.
Then run:

RepoAlign: Analyze Staged Changes
Expected:

It says no staged changes to analyze.
4. Create a Python Change
Open a Python file, for example:

def format_greeting(name):
    return f"Hello, {name}!"
Change it to something like:

def format_greeting(name):
    cleaned = name.strip()
    return f"Hello, {cleaned}!"
Save the file.

5. Stage the File
Use VS Code Source Control panel:

Open Source Control.
Click + beside the changed Python file.
Or use terminal inside the test project:

git status
git add path/to/your_file.py
git status
Expected:

File appears under staged changes.
6. Test 10.1: Staged Git Integration
Run:

RepoAlign: Inspect Staged Changes
Expected in RepoAlign output channel:

staged file count
file path
status like M
additions/deletions
staged diff text
Example:

RepoAlign Staged Changes

Staged files: 1

Files
-----
M helper.py (+2/-1)

Staged Diff
-----------
@@ ...
This proves RepoAlign can inspect what you are about to commit.

7. Test 10.2 and 10.3: Diff Parser and Symbol Extraction
Run:

RepoAlign: Analyze Staged Changes
Expected:

Progress notification appears.
It parses staged hunks.
It maps changed lines to Python symbols.
Output channel shows request summary.
Look for:

RepoAlign Staged Commit Analysis

Request Summary
---------------
Files: 1
Changed Python symbols: 1
If you changed inside a function/class, Changed Python symbols should be at least 1.

8. Test 10.4: Payload Contract
Open backend Swagger:

http://localhost:8000/docs#/
Find:

POST /api/v1/analyze-staged-changes
Click it and inspect schema.

Expected request model contains:

workspaceId
workspaceName
backendUrl
files
path
status
oldContent
newContent
hunks
changedSymbols
This proves the frontend/backend staged payload contract exists.

9. Test 10.5: Backend Commit Analysis Endpoint
After running:

RepoAlign: Analyze Staged Changes
Expected output contains backend response like:

{
  "status": "ok",
  "recommendation": "ready",
  "summary": {
    "total_files": 1,
    "python_files": 1,
    "total_hunks": 1,
    "total_changed_symbols": 1
  },
  "changed_symbols": [...],
  "diagnostics": [...]
}
Recommendations:

ready: no obvious issue
review: needs attention or context retrieval had warning
blocked: staged Python syntax error found
10. Test Syntax Error Detection
Stage a broken Python change:

def broken_function(
    return "bad"
Then run:

RepoAlign: Analyze Staged Changes
Expected:

Backend response has diagnostic like syntax error.
Recommendation becomes:
blocked
Then fix the syntax and stage again.

11. Confirm GitHub Push Is Not Blocked
After all tests, run normal Git commands:

git status
git commit -m "test staged analysis"
git push
Expected:

RepoAlign does not block commit.
RepoAlign does not block push.
No Git hook was installed.
Normal GitHub workflow works.
Quick Final Pass
For presentation, the best demo sequence is:

RepoAlign: Inspect Staged Changes
RepoAlign: Analyze Staged Changes
Show:

staged file diff
changed symbol count
backend recommendation
then say clearly: “RepoAlign is advisory here; it does not block Git push.”


Here is the step-by-step test for Phase 10.6 to 10.10.

Before You Start
Start backend first:

http://localhost:8000/docs#/
Make sure this endpoint exists:

POST /api/v1/analyze-staged-changes
Then launch extension debugger:

Open RepoAlign/frontend in VS Code.
Press F5.
In the new Extension Development Host, open your Python test repo.
1. Prepare a Clean Passing Change
In your test repo, edit a Python file with valid code.

Example:

def format_greeting(name):
    cleaned = name.strip()
    return f"Hello, {cleaned}!"
Stage it:

git add path/to/file.py
git status
Expected: file is staged.

2. Test 10.6: Commit With Analysis
In Extension Development Host:

Ctrl + Shift + P
RepoAlign: Commit With Analysis
Expected:

RepoAlign runs staged analysis.
RepoAlign output channel opens.
You see recommendation, staged files, findings.
If recommendation is ready, it asks for commit message.
Enter message, for example:
test: commit with repoalign analysis
Expected:

Git commit completes.
Output channel shows Git Commit Result.
Output records successful analysis event.
3. Test 10.8: Normal Pass-Through
After the clean commit, run:

git log --oneline -1
git status
Expected:

Latest commit is your message.
Working tree/staged area is clean.
RepoAlign did not interrupt the clean commit.
Also confirm push still works normally:

git push
Expected:

RepoAlign does not block push.
4. Test 10.9: Blocking Result Model
Now create a bad staged Python change.

Example:

def broken_function(
    return "bad"
Stage it:

git add path/to/file.py
Run:

RepoAlign: Analyze Staged Changes
Expected in RepoAlign output:

Recommendation: blocked
Findings section includes:
severity: blocker
affected file
reason: syntax error
matched pattern: python-syntax-error
suggested fix
validation status: failed
5. Test 10.6 Blocking Behavior
With the bad change still staged, run:

RepoAlign: Commit With Analysis
Expected:

Commit is blocked.
No commit message box should complete the commit.
Output channel shows blocker finding.
File remains staged.
Verify:

git log --oneline -1
git status
Expected:

Latest commit did not change.
Bad file is still staged.
6. Fix and Commit After Resolution
Fix the syntax:

def broken_function():
    return "good"
Stage again:

git add path/to/file.py
Run:

RepoAlign: Commit With Analysis
Expected:

Recommendation becomes ready or review.
If review, choose Commit Anyway.
Enter commit message.
Commit succeeds.
7. Test 10.7: Install Optional Hook
Run:

RepoAlign: Install Pre-Commit Hook
Expected:

VS Code shows hook installed.
Check file exists:
Test-Path .git/hooks/pre-commit
Get-Content .git/hooks/pre-commit
Expected content includes:

RepoAlign managed pre-commit hook
8. Test Hook Pass Case
Make a valid Python change and stage it:

git add path/to/file.py
git commit -m "test: hook pass"
Expected:

Hook runs.
It prints RepoAlign recommendation.
Commit succeeds.
9. Test Hook Block Case
Create a Python syntax error again and stage it:

git add path/to/file.py
git commit -m "test: hook block"
Expected:

Hook blocks commit.
Terminal shows RepoAlign blocker message.
Commit does not happen.
To confirm:

git log --oneline -1
git status
10. Test Hook Bypass
Only for demonstration:

git commit --no-verify -m "test: bypass repoalign hook"
Expected:

Commit bypasses the optional hook.
This proves users can still escape enforcement if needed.
11. Remove Hook
Run:

RepoAlign: Remove Pre-Commit Hook
Expected:

Hook removed.
Confirm:

Test-Path .git/hooks/pre-commit
Expected:

False
Best Demo Flow
For your final presentation, show this order:

RepoAlign: Analyze Staged Changes
RepoAlign: Commit With Analysis
RepoAlign: Install Pre-Commit Hook
git commit -m "demo"
RepoAlign: Remove Pre-Commit Hook
git push
Key sentence to say:
“RepoAlign gives a controlled commit-time gate, but normal GitHub push is never blocked by the extension.”