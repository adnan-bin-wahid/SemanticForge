# RepoAlign Onboarding Smoke Test

Use this checklist to prove a new user can start RepoAlign from a clean VS Code session.

## Manual Test

1. Start the RepoAlign backend stack.
2. Open a Python Git repository in VS Code.
3. Launch the extension debugger from `RepoAlign/frontend`.
4. Confirm the RepoAlign welcome panel appears.
5. Run `RepoAlign: Validate Workspace`.
   Expected: ready message with a Python file count.
6. Run `RepoAlign: Backend Readiness Check`.
   Expected: FastAPI, Neo4j, Qdrant, and Ollama/model are reported in the `RepoAlign` output channel.
7. Run `RepoAlign: Analyze Workspace`.
   Expected: progress notification, success message, and indexing report in the `RepoAlign` output channel.
8. Run `RepoAlign: Indexing Status`.
   Expected: last indexed time, backend URL, file counts, and graph status are shown.
9. Save a Python file.
   Expected: the `RepoAlign` output channel records the synced file, and `/full-maintenance-loop/status` shows activity.
10. Run `RepoAlign: Re-index Embeddings`.
    Expected: Qdrant embedding indexing succeeds and reports indexed symbol count.
11. Run `RepoAlign: Reset Workspace Graph/Index`.
    Expected: Neo4j graph and Qdrant collection are cleared, local indexing state is removed, and `RepoAlign: Indexing Status` says the workspace has not been indexed yet.
12. Run `RepoAlign: Rebuild Graph`.
    Expected: the workspace indexes again successfully.

## Scripted Test

From `RepoAlign/frontend`:

```powershell
npm run compile
npm run smoke -- -WorkspacePath "E:\path\to\python-repo"
```

The smoke script checks:

- extension command registrations for onboarding, indexing, reset, rebuild, and embeddings
- backend readiness
- graph status endpoint
- optional workspace validation for Git and Python files
