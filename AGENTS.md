# Repository instructions

Read `CLAUDE.md` for the shared project architecture, commands, engineering
standards and security rules. Those instructions apply to Codex contributors too.
Read `docs/DEVELOPMENT_WORKFLOW.md` before planning or implementing changes.
For concurrent implementation, also follow `docs/PARALLEL_DEVELOPMENT.md`: use
separate worktrees and branches, claim one ready item, and isolate test/runtime
resources. Jira assignment alone does not reserve files or make a shared checkout safe.

Use Jira project `KAN` for epics, stories, bugs, acceptance criteria and current
delivery status. Search for existing work before creating an item. Reconcile
historical plans against current code, tests and GitHub PRs before importing work.
Include the real Jira key in new branch names, commit subjects and PR titles.
Never invent a key or claim an external update succeeded without verifying it.

Preserve other contributors' uncommitted changes. A merge to `main` can trigger
production deployment; obtain the required release approval before merging.
