# Parallel development and delivery order

This is the implementation policy for Codex and Claude Code working on KAN.
The agent account IDs and ready-queue queries are in
[the shared workflow](DEVELOPMENT_WORKFLOW.md#agent-work-queues).

## Isolation before implementation

Each concurrent implementation session needs its own Git worktree, branch,
dependency installation and writable runtime/test resources. Two branches in
one directory are not isolation: switching branch changes that directory for
both sessions. Worktrees isolate file changes, but do not by themselves isolate
databases, processes, ports, cookies or external services.

- Codex: use the app's Worktree mode or a managed worktree. Confirm the actual
  working directory and base commit; make a named branch before publishing a PR.
- Claude Code: the installed CLI supports `claude --worktree KAN-77-figures`.
  This is an example launch command, not evidence that a session has been started.
  Confirm the created directory, branch and base commit before editing.
- Branches must contain their real Jira key, for example
  `codex/KAN-146-alert-evaluation`. Never switch or reset the other agent's branch.
- Start from an up-to-date reviewed base. Check existing worktrees and active
  sessions before reusing a checkout; an old worktree name does not prove it is free.
- Keep each worktree's `.venv`, `node_modules`, test temporary directories,
  coverage output and build output separate. Shared package download caches are
  acceptable; neither agent may globally prune them or kill the other's processes.

The Codex [worktree guide](https://learn.chatgpt.com/docs/environments/git-worktrees)
explains app checkout isolation. Git worktrees start from committed content unless
a tool explicitly carries local changes. Do not assume untracked instruction files
or these uncommitted workflow edits are present in a new checkout.

Until the KAN-2 workflow changes are committed and available on both branches,
explicitly read the prepared `AGENTS.md`, `CLAUDE.md`, shared workflow and this policy
from the primary checkout as read-only instructions in both sessions. Record the
instruction source in the handoff. Publishing these rules remains KAN-2 work;
KAN-2's first-linked-PR criterion must not circularly prevent creating that first PR.

## Claim and overlap preflight

Before editing an implementation item:

1. Read its live assignee, status, acceptance criteria, parent and dependencies.
2. Read all KAN items in progress or review and relevant open GitHub PRs. A missing
   issue link is not evidence that two changes cannot overlap.
3. Confirm there is no other writing session for this ticket or branch. Each agent
   owns one primary implementation item at a time; focused subagents work under
   that item's coordinator with explicit file ownership.
4. Record the worktree path, branch, base commit, intended files/contracts,
   validation approach and any reserved runtime resources in the ticket handoff.
   Keep secrets and full credential-bearing URLs out of it.
5. Re-read the claim and competing work, then move the item to `In Progress` when
   implementation actually begins. If ownership is ambiguous, resolve it before
   editing. Jira assignment and comments are coordination records, not atomic locks.

Reserve shared boundaries before changing them: feed/store query ports, shared
hooks and UI primitives, OpenAPI and generated clients, Alembic migration heads,
lockfiles, Compose, CI and shared workflow/history documents. One agent owns a
boundary change; dependent work uses the existing contract or waits for the PR
to integrate. Avoid incidental refactors outside the active ticket.

For the first batch, Codex owns warning evaluation and any supporting event-query
contract changes in KAN-146/148/147. Claude's KAN-77 can stay in `FiguresPage.tsx`
and its existing figures tests without changing shared `useResource`. Before
KAN-27, Claude checks Codex's active store/cooperative-read work and uses the
existing cooperative boundary, or records and waits for the dependency.

## Test and runtime separation

The first pair, KAN-146 and KAN-77, can run focused tests with synthetic events and
MSW. They do not require live feeds, PostgreSQL, Compose or a production database.

For ordinary backend tests, ensure the test process does not inherit
`ASE_TEST_DATABASE_URL`, `ASE_TOKEN_RACE_TEST_URL` or the integration-test
`ASE_*_POSTGRES_URL` variables. The default test fixture uses private in-memory
SQLite. A configured shared database can be dropped and recreated by
`backend/tests/pytest_support.py`; its xdist check does not protect two independent
serial pytest processes. When PostgreSQL is required, allocate a distinct,
disposable database per agent and serialise the relevant tests within that database.

Do not share editable Python installations across worktrees, because imports can
resolve to the other checkout. Run focused tests in parallel, but coordinate full
coverage suites and performance benchmarks to avoid competing for the same CPU
and invalidating timing evidence. Run all required checks before review.

If native servers become necessary, record and verify these per-agent settings:

| Resource | Required separation |
| --- | --- |
| API and frontend ports | Distinct ports, for example API 8001/8002 and Vite 5173/5174; check availability first. |
| Frontend proxy | Each `ASE_DEV_API_TARGET` points to its own API; each backend `ASE_PUBLIC_BASE_URL` matches its frontend origin. |
| Database | Each `ASE_DATABASE_URL` names only its own new disposable database or worktree-local SQLite file. |
| Writable feed state | Private `ASE_SATELLITE_CACHE_DIR`; disable `ASE_LIVE_SNAPSHOT_PATH` or use a private file. |
| Background work | Use a fresh database with no real schedules or credentials; disable feeds and archive fetching for offline work. |
| Browser session | Separate browser profiles or separately verified loopback hostnames, used consistently. |

Ports alone do not isolate the `ase_refresh` and `ase_csrf` cookies: they are scoped
to the host, not the port. Distinct loopback hostnames require verified resolution
and binding; none have been configured by this policy change. Setting
`ASE_FEEDS_ENABLED=false` and `ASE_ARCHIVE_ENABLED=false` does not disable all
schedule, report or annotation workers. Never point these workers at another
agent's database or a copy containing real scheduled jobs/provider credentials.

Compose requires additional preparation: separate project names and private bind
mounts, plus explicit host-port replacements. The existing file publishes 80/443
and binds `./data`; a project name alone is insufficient. API containers migrate
their configured database on startup. Neither initial ticket needs Compose, so do
not start or modify the shared stack merely to run its focused tests.

## Prioritisation

Priority expresses impact and urgency. The small `agent-ready` queue, ordered by
native Jira Rank, expresses what to implement next. The label is a planning gate,
not a workflow status or permission to skip the preflight. Resume a genuinely
claimed item, otherwise take the first unblocked ready item assigned to that agent.
Review dependencies and unmerged overlapping PRs before moving to the next item.

Initial order, reviewed 28 September 2026:

| Agent | Order | Jira item | Why it is here |
| --- | --- | --- | --- |
| Codex | 1 | [KAN-146](https://alex-orr.atlassian.net/browse/KAN-146) | Reproduced missed alerts even when a rule is satisfied. |
| Codex | 2 | [KAN-148](https://alex-orr.atlassian.net/browse/KAN-148) | Reproduced false alerts from future timestamps; finish the same evaluator boundary serially. |
| Codex | 3 | [KAN-147](https://alex-orr.atlassian.net/browse/KAN-147) | Reproduced loss of retained maritime warnings and space context. |
| Claude | 1 | [KAN-77](https://alex-orr.atlassian.net/browse/KAN-77) | A request loop amplifies an API availability defect. |
| Claude | 2 | [KAN-27](https://alex-orr.atlassian.net/browse/KAN-27) | Legitimate figures requests still block the API after the request-loop fix. |
| Claude | 3 | [KAN-151](https://alex-orr.atlassian.net/browse/KAN-151) | Invalid replacements delete accepted photo inputs and clear analysis. |

KAN-146, KAN-147 and KAN-151 are High because they are reproduced correctness or
data-loss defects. KAN-148 remains Medium: its supplied future timestamp reproduces
the problem offline, with no verified currently affected provider. It still follows
KAN-146 in Rank to finish that shared boundary. KAN-15 remains Medium hardening:
the redactor fails for nested secrets, but no current exposing log call was found.

Review later batches by demonstrated impact, dependencies, effort, uncertainty and
overlap. Give confirmed availability, data-loss and access-control failures priority,
then correctness and essential accessibility, before broad refactoring and new
features. A small prerequisite may move forward to unblock a more valuable item.
Do not equate security severity with delivery priority or ticket count with effort.

Possible next candidates are KAN-15 and KAN-153 for Codex, and KAN-150 and KAN-78
for Claude. They are not part of the initial ready batch. Keep KAN-6's broad
refactoring and new feature work behind the first defect batch unless Alex changes
the order. When the ready queue is empty or blocked, report it and review the next
batch; do not silently treat all 70 owned items as permission for continuous work.

## Review, integration and release

Use one focused PR per primary item, with Jira key, validation evidence, overlapping
PRs, shared-boundary ownership and required merge order. Worktrees prevent file
overwrites but cannot prevent incompatible changes that Git merges cleanly.

Integrate serially: review and validate one PR, obtain the required release approval,
then merge it. Update the next affected branch from the resulting `main`, resolve
conflicts and rerun relevant combined-state checks before approving its merge.
Do not force-push or rewrite another contributor's shared branch to achieve this.

On 28 September 2026, GitHub's effective main-branch rules require PRs, resolved
review threads, up-to-date CI checks and code-scanning gates. They require zero
approving reviews, so human release approval remains a process requirement rather
than an enforced reviewer count. Successful `main` CI can trigger production
deployment. This policy does not change GitHub rules or enable automatic merging.

Checkout isolation and GitHub checks are technical controls. Claims, runtime
reservations, sequencing and release approval still require agents to follow this
policy and Alex to authorise release. Confirm the setup at the start of each session;
do not describe written rules as proof that both running environments are isolated.
