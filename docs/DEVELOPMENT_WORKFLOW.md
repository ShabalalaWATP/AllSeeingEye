# Jira development workflow

Jira tracks priorities, scope, acceptance criteria and delivery status. GitHub
tracks source changes, review and CI. Repository documents retain architecture,
decisions and implementation evidence. Both Codex and Claude Code use this flow.

## Project and connections

- Jira: [OSINT, project KAN](https://alex-orr.atlassian.net/jira/software/projects/KAN/list?jql=project%20%3D%20KAN).
- GitHub: [ShabalalaWATP/AllSeeingEye](https://github.com/ShabalalaWATP/AllSeeingEye).
- Official MCP endpoint: `https://mcp.atlassian.com/v2/mcp`.
- Codex desktop: install and authorise the Atlassian Rovo plugin for the intended
  site, then verify access by reading a KAN work item.
- Claude Code: register the endpoint using
  `claude mcp add --transport http --scope user atlassian https://mcp.atlassian.com/v2/mcp`.
  Open a new Claude Code session, run `/mcp`, select `atlassian` and authenticate.
  Verify access with a read of the same KAN item. Each client needs its own login.
- GitHub for Atlassian links development activity when a real Jira key appears
  in the branch name, commit subject and PR title. Verify repository access and
  synchronisation in Jira's GitHub configuration page.

Prefer OAuth. Never put tokens, auth headers, passwords or real `.env` values in
the repository, Jira descriptions, PRs or agent handoff notes. A connection does
not authorise unrelated external messages, production changes or expanded access.
Avoid adding a duplicate Codex MCP server if the plugin already supplies it.

Setup references: [Atlassian MCP](https://developer.atlassian.com/cloud/rovo-mcp/guides/getting-started/),
[Codex MCP](https://developers.openai.com/codex/mcp),
[GitHub for Atlassian](https://support.atlassian.com/jira-cloud-administration/docs/integrate-with-github/).

## Agent work queues

Jira assignees identify the agent responsible for each work item. Assignment does
not start a coding session. When Alex asks an agent to check its work or take the
next ticket, use the queue for the client actually doing the work:

| Client | Jira assignee | Account ID |
| --- | --- | --- |
| Codex | `alexcodex` | `712020:ca9e479a-69f4-4e7e-8aba-45a1b3348307` |
| Claude Code | `alexclaude` | `712020:75780a4b-d249-4726-92d9-aec87cbaed66` |

Codex's ready implementation queue:

```jql
project = KAN AND assignee = "712020:ca9e479a-69f4-4e7e-8aba-45a1b3348307"
AND statusCategory != Done AND issuetype != Epic
AND labels = "agent-ready"
ORDER BY Rank ASC
```

Claude Code's ready implementation queue:

```jql
project = KAN AND assignee = "712020:75780a4b-d249-4726-92d9-aec87cbaed66"
AND statusCategory != Done AND issuetype != Epic
AND labels = "agent-ready"
ORDER BY Rank ASC
```

Use the explicit account ID even if the MCP connection is authorised as Alex's
main account. `currentUser()` means the connector's signed-in Jira user, which may
not be the agent assignee. Remove the label clause to inspect the full owned
backlog; also remove the type clause to include owned epics. Priority describes
impact/urgency, while Rank orders the deliberately small ready queue. Do not add
`priority DESC` to the ready query: it would override the reviewed sequence.

Resume an owned, claimed implementation item first. Otherwise, take the first
unblocked `To Do` item from the ready queue after the preflight in
[parallel development](PARALLEL_DEVELOPMENT.md). Check all active items and PRs
for overlapping work, not just explicit Jira dependency links. When the ready
queue is empty or blocked, report that and review the next batch with Alex;
do not start an arbitrary owned backlog item. An explicit request for a particular
ticket can change the queue, but does not waive isolation or release rules.

The live Jira assignee is the source of truth; do not take another agent's item or
silently reassign it. An epic owner coordinates the outcome, while each child's
assignee owns its implementation. Keep one primary implementation item active per
agent unless Alex explicitly requests parallel work within that agent's queue.
KAN-2 and KAN-3 are setup/adoption records; their existing `In Progress` status does
not prove a coding session is running or consume an implementation slot. They still
need their outstanding evidence, including the first linked PR and a Claude read.

Initial ready order, 28 September 2026:

| Order | Codex | Claude Code |
| --- | --- | --- |
| 1 | KAN-146: missed alert matches | KAN-77: figures request loop |
| 2 | KAN-148: future-dated false alerts | KAN-27: figures event-loop stalls |
| 3 | KAN-147: lost maritime/space context | KAN-151: destructive photo replacement |

These six cards carry `agent-ready` and their native Jira ranks express this
order. The remaining backlog is assigned, not fully sequenced. Review subsequent
batches by demonstrated impact, dependencies, scope and effort. Equal ticket
counts do not imply equal effort. The prioritisation rationale and shared-boundary
reservations are in [parallel development](PARALLEL_DEVELOPMENT.md).

The initial split groups backend, security, operations, CI and technical
documentation under Codex, and UI, accessibility and related analyst workflows
under Claude Code. Related fixes can cross these broad areas while sharing one
owner. Ownership does not authorise credential rotation, production changes,
merges or other actions that still require Alex's approval.

## Work hierarchy

- **Epic:** a coherent outcome delivered by multiple stories or tasks.
- **Story:** a bounded user-visible improvement with observable acceptance criteria.
- **Task:** engineering, investigation, configuration or validation work.
- **Bug:** observed incorrect behaviour, reproduction steps and expected behaviour.
- **Subtask:** a small part of a parent item, such as a test or documentation change.

Use the types and transitions actually available in KAN. Do not assume an epic,
status or custom field exists, or alter project-wide configuration silently.
Create an epic only when it groups real work; small fixes can stand alone.

Each actionable item needs a problem or outcome, scope, acceptance criteria,
validation approach, relevant dependencies and links to the code or design context.
Keep sensitive operational evidence out of broadly visible work items.

KAN currently provides `To Do`, `In Progress`, `In Review` and `Done` for its
work types (verified 28 September 2026). The starter epic is
[KAN-1](https://alex-orr.atlassian.net/browse/KAN-1), with
[workflow adoption, KAN-2](https://alex-orr.atlassian.net/browse/KAN-2),
[agent connection validation, KAN-3](https://alex-orr.atlassian.net/browse/KAN-3)
and [backlog reconciliation, KAN-4](https://alex-orr.atlassian.net/browse/KAN-4).

## Before implementation

1. Read the requested Jira item and search for existing matching items and PRs.
   If Alex requests a new improvement without a key, create a bounded KAN item
   within that authorised scope. Do not create unrelated roadmap work.
2. Check current code, tests, recent commits and relevant plans. Old unchecked
   boxes are leads for investigation, not proof that a feature is missing.
3. Confirm acceptance criteria and dependencies. Link the parent epic where useful.
4. Complete the concurrency preflight, record the worktree, branch, base commit
   and file/contract ownership. Concurrent implementation requires separate
   checkouts. Do not rename, reset or clean another session's branch or checkout.
5. Move the item to an available in-progress status when work actually starts.

If Jira is unavailable, record the intended item and acceptance criteria locally,
report the connection blocker and continue authorised reversible local work.
Reconcile with Jira before opening the PR. Do not fabricate an issue number.

## Git and review

When Alex explicitly requests a backlog-wide batch, record the selected items
and dependency order before implementation. Group related items in a PR at the
requested approximate size, with one primary key and explicit acceptance
evidence for each additional key. That request may expand the initial ready
queue; it does not waive ownership, independent review, isolation or release
approval. The current delivery register is linked from the documentation index.

For a real item whose key is `KAN-123`, illustrative names are:

```text
Branch: codex/KAN-123-feed-recovery
Commit: fix(KAN-123): preserve feed recovery state
PR:     KAN-123: Preserve feed recovery state
```

Use the applicable branch convention with the Jira key included. Keep each PR
focused on one primary item; explicitly link any additional items. Use the PR
template to state the behaviour, acceptance evidence and security or migration
implications. Do not treat `Closes KAN-123` as automatic Jira closure.

Run relevant checks and record the exact results. Use existing coverage gates and
required independent reviews. Record failures and skipped checks honestly. Move
to an available review status when the change is ready for review; if the board
has no review status, retain in-progress and link the review evidence.

## Completion and release

Mark an implementation item done only when its acceptance criteria are met,
required checks and review pass, and the change is merged through the authorised
workflow. For non-code tasks, use their explicit deliverable and validation criteria.
Track blocked work with a reason and dependency using the project's existing fields.

This repository's successful CI on `main` can trigger production deployment.
Merging therefore requires the applicable release approval. Connector access or a
Jira transition does not grant that approval. Do not enable automatic Jira closure
or new deployment automation as part of routine story implementation.

Keep release evidence explicit: merged commit, deployment run and verification
result. When live acceptance is required, keep it as an outstanding criterion or
linked validation item. A merge or an offline test is not proof of a live release,
provider connectivity, research accuracy or successful backup recovery.

## Agent handoff

Update the Jira item with a concise, factual handoff within the requested work:
key, branch and HEAD, relevant PR, file ownership, completed acceptance evidence,
remaining work and blockers. Link durable repository documentation. Never copy
credentials, raw private logs or unrelated conversation content into Jira.

## Bringing existing work into Jira

Start by reconciling the current branch, recent merged PRs and plan completion
registers. Create items only for confirmed remaining work or explicit validation
gaps. Record completed historical milestones as context where useful, rather than
creating a backlog that asks agents to reimplement them.

Initial reconciliation areas are research and subscriptions acceptance, operations
and recovery, research-quality and browser/export acceptance, and recent reliability
and catalogue rollout. These are investigation areas, not claims of missing features.
