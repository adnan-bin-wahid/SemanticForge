# Pattern Detection Evaluation

Use `pattern_detection_cases.json` as the Phase 11 demonstration checklist.

For each case:

1. Create or stage the described Python change in a small test repository.
2. Run `RepoAlign: Analyze Staged Changes`.
3. Confirm the output contains the expected recommendation or finding pattern.
4. For intentional deviations, run `RepoAlign: Ignore Finding Once` or `RepoAlign: Ignore Finding Pattern`.
5. Run analysis again to confirm the ignored finding is suppressed.

Minimum presentation target:

- 3 aligned examples with no active drift finding.
- 3 deviating examples with `return-style-drift`, `helper-call-drift`, or `exception-flow-drift`.
- 1 blocking syntax example.
- 1 ignore-once demonstration.
- 1 ignore-pattern demonstration.
