# KAN-216 acceptance and closure record

Reviewed 10 October 2026. The batch contains 32 tickets, represented by 30 delivery
PRs (#162–#191) and aggregate PR #192. PR #191 groups KAN-165, KAN-168 and KAN-172.
Every delivery PR head is an ancestor of integration revision `ca810947`.

This record distinguishes completed documentation, reviewed implementation and
outstanding operator decisions. It does not authorise merge or deployment.

## Closure matrix

“Await integration” means the implementation can close after final applicable
checks pass and it is merged through the authorised aggregate. Separate production
enablement is not required unless explicitly stated below.

| Ticket | Delivery PR | Acceptance position |
| --- | --- | --- |
| KAN-164 | #175 | Operator decision outstanding: software licence, offer and trading details. Neutral decision record can integrate. |
| KAN-165 | #191 | Operator/publication approval outstanding. Draft pages and enforcement can integrate; approved content cannot be inferred. |
| KAN-166 | #184 | Enquiry admission and PostgreSQL checks reviewed; await integration. |
| KAN-167 | #185 | Administration, retention and erasure reviewed; await integration. |
| KAN-168 | #191 | Public form and contact navigation reviewed; final contact screenshots recorded separately; await integration. |
| KAN-169 | #189 | Administrator workspace, focus and reflow reviewed; final contrast evidence recorded separately; await integration. |
| KAN-172 | #191 | Agreed mobile 90 target met in three runs; footer completion at `eac313fb` requires final aggregate evidence and integration. |
| KAN-182 | #183 | Idle expiry, session ownership and race regressions reviewed; await integration. |
| KAN-184 | #178 | External embed consent reviewed; final sanitised network evidence recorded separately; await integration. |
| KAN-194 | #180 | Catalogue completeness and provenance repaired at `ca810947`; focused checks and independent review pass; await integration. |
| KAN-195 | #188 | Commercial admission, retained evidence and integration boundaries reviewed; await integration. |
| KAN-206 | #181 | Brief remount and globe fixture reliability reviewed; await integration. |
| KAN-217 | #171 | Durable alert-report admission reviewed; await integration. |
| KAN-218 | #176 | Frozen scope and evidence reviewed; await integration. |
| KAN-219 | #179 | Executable template validation and legacy recovery reviewed; await integration. |
| KAN-220 | #186 | Consumed evidence, atomic admission and migration guards reviewed; await integration. |
| KAN-221 | #177 | Frozen edition links and unavailable targets reviewed; await integration. |
| KAN-222 | #168 | Unsaved Brief navigation protection reviewed; await integration. |
| KAN-223 | #169 | Stable unique indicator identifiers reviewed; await integration. |
| KAN-224 | #172 | Unsupported private-input choices and existing-reference preservation reviewed; await integration. |
| KAN-225 | #163 | Live control outstanding: approved environment settings and both gate outcomes. Proposal/workflow can integrate first. |
| KAN-226 | #170 | Done: validated non-code security refresh procedure. Merge and operational execution remain separate. |
| KAN-227 | #164 | Dependency/image repairs and security gates reviewed; await integration. |
| KAN-228 | #174 | Uncertain webhook acceptance and retry semantics reviewed; await integration. |
| KAN-229 | #182 | Subscription edits, pinned scope and history reviewed; await integration. |
| KAN-230 | #173 | Done: validated non-code CI documentation, including current 90 acceptance and 150 KiB product budget. |
| KAN-231 | #190 | Required synthetic browser journeys reviewed; await integration. |
| KAN-232 | #187 | Responsibility splits and unchanged source-size enforcement reviewed; await integration. |
| KAN-233 | #165 | Saved-map authentication and bounded admission reviewed; await integration. |
| KAN-234 | #166 | Originating-session request/refresh binding reviewed; await integration. |
| KAN-235 | #167 | Feed TLS identity and cookie isolation reviewed; await integration. |
| KAN-236 | #162 | Semantic-search session fences reviewed; await integration. |

Totals: two completed non-code deliverables, 27 implementation tickets awaiting
authorised integration, and three operator/live-control items.

Commands, limitations and historical failures remain in the
[implementation ledger](KAN-216-implementation-ledger.md), per-ticket review
records, [public-page acceptance](../PUBLIC_PRODUCT_PAGE_ACCEPTANCE.md) and
[catalogue provenance review](KAN-194-provenance-closure.md).
The [final browser evidence](KAN-216-final-browser-evidence.md) supplies complete
contact screenshots, native contrast resolution and a sanitised consent capture.
Provider permissions remain unresolved where recorded; catalogue completion
does not grant those permissions.

## Final evidence boundary

Combined revision `99bff8f9` passed all 40 checks. Documentation revision
`ab9bb474` also passed all 40 checks during the closure review. Neither
result establishes green CI for the later footer and catalogue changes.
The final aggregate revision must pass its required checks before merge.

The Semgrep logout alert 5044 is dismissed as a reviewed false positive:
`LogoutUseCase.execute` is not a SQL cursor. Its cookie input is hashed and the
repository uses bound SQLAlchemy expressions. PR #192's associated review thread
is resolved. Recheck review/check state after subsequent changes.

## Integration and release order

1. Finish final aggregate evidence, record the exact tested head, resolve remaining
   findings and mark PR #192 ready.
2. Obtain explicit approval for the aggregate merge and its release implications.
   Main CI can trigger deployment; Jira closure is not that approval.
3. Merge PR #192 through the existing required-check and squash-merge rules.
   Separate prerequisite merges are unnecessary: their reviewed heads and
   combined fixes are already present.
4. Verify the merged commit, then close eligible implementation tickets with that
   commit and their original delivery PR as evidence.
5. Complete operator decisions and the separately approved manual rollout.
   Code integration is not public launch or live acceptance.

No deployment-gate change is needed merely to integrate this code. KAN-164 does
not block neutral, gated implementation. KAN-225's harmless approve/reject
verification requires its workflow on main, so live acceptance follows integration.

KAN-165 blocks deployment: the controller checks publication approval
unconditionally, even with product and enquiry flags disabled. Approval remains
unset. Production rollout requires the operator facts, service wording and
exact-content approval documented in [publication guidance](../PUBLIC_POLICY_PUBLICATION.md).

Migrations 0090–0094 form one chain and require the documented manual rollout.
Apply migrations before new workers. Backout must preserve retained evidence
and enquiries, drain or cancel pending alert admission and stop warning workers
before older code runs. Image rollback alone does not reverse those contracts.
Reviewed deployment-controller changes also require operator installation.

## Preserve delivery provenance

Before closing superseded PRs, retain each ticket's original PR URL and head SHA,
the tested aggregate SHA and the resulting main commit in the closure evidence.
A squash merge may not mark the source PRs merged automatically.

After the authorised aggregate merge is verified, close #162–#191 as superseded
by #192, linking the aggregate commit. Do not claim those individual PRs were
merged. Preserve review discussions and CI evidence. Do not merge them again,
and do not close KAN-164, KAN-165 or KAN-225 merely because their proposal or
gated implementation entered main.
