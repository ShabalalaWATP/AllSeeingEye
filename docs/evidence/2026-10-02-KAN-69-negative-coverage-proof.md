# KAN-69 acceptance reconciliation

The deliberately labelled WIP [PR 125](https://github.com/ShabalalaWATP/AllSeeingEye/pull/125)
was closed **unmerged** at 2026-10-02 21:59:28 UTC. Final readback proves CLOSED,
null merge commit/time, no auto-merge and zero changed files. No release or
deployment resulted from this proof PR.

## Real negative gate and exact restoration

Frozen known-green base: `13e9525d904e744e0bc7ea329e8d475234f86f25`.
Negative head: `f24d0cd68960a88bb2a676687caddf33cb9bd7c8`. Its only change was the
two-line DOM setup skip hook, with production, workflows, exclusions, checkers
and thresholds unchanged.

[Negative CI 37066328868](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/37066328868)
completed. All four frontend shards, the four-blob census and every other CI job
passed. Only merged frontend coverage and its dependent frontend check failed.
Vitest explicitly rejected 13.93% branches against the unchanged 90% gate.
Independent JSON/LCOV reconciliation gives 3,513/25,205 branches,
4,527/24,102 lines and 919/9,168 functions. Test result: 824 passed and 3,571
deliberately skipped. The separate auth policy failed too; its following Python
branch-policy command was not reached, so that is not claimed as extra proof.

Normal revert `2c35f291f732bbb4b92fc68eed89dd151938de7e` restores the entire Git tree
exactly to the frozen base. [Restoration CI 37068058961](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/37068058961)
passed, and all 38 final PR checks succeeded. Both runs were observed once, with
no retry, force-push, main merge or deployment. Raw logs, four blobs, JSON/LCOV,
run metadata, tree identity and final PR state are retained privately in
`C:/Users/alexo/.codex/scratch/kan69-negative-github-13e9525d/`.

## Existing five-before/five-after timing evidence

The live criterion asks for `gh run view --json jobs` timings from five runs
before and after, and each shard at most six minutes including setup. The
committed census already contains five before and five after observations.
Independent review re-read the five successful before workflows:

| Run         | Complete frontend job, seconds |
| ----------- | -----------------------------: |
| 36502935364 |                           1013 |
| 36504362633 |                            965 |
| 36505778000 |                           1038 |
| 36507371831 |                           1042 |
| 36508802767 |                           1066 |

Frontend was the final job in each. A stronger retained after cohort consists of
five wholly successful workflows:

| Run         | Shards 1–4, complete job seconds | Whole frontend path | Seconds before final PostgreSQL job |
| ----------- | -------------------------------- | ------------------: | ----------------------------------: |
| 37005545521 | 289 / 308 / 293 / 289            |                 353 |                                 647 |
| 37011600827 | 299 / 257 / 256 / 199            |                 339 |                                 596 |
| 37019394842 | 248 / 336 / 290 / 289            |                 379 |                                 560 |
| 37034703344 | 294 / 303 / 293 / 280            |                 352 |                                 432 |
| 37043269376 | 288 / 246 / 300 / 293            |                 339 |                                 597 |

All 20 after shards meet six minutes, with a maximum of 336 seconds (5m36s).
Setup and post-job actions are included. Frontend is off the observed critical
path in all five runs. Their frontend trees, locks and three relevant workflows
(`frontend.yml`, `ci.yml`, `deploy.yml`) are byte-identical. Metadata lives in the
five `ci-<run>` directories under
`C:/Users/alexo/.codex/scratch/kan71-73-followup-58c5b2fe/`.

The original committed after cohort has a 263-second maximum, but only two whole
workflows succeeded. Preserve that historical qualification. The before/after
comparison crosses source, dependencies, test populations and workflow changes;
hosted placement, load and cache warmth were uncontrolled. This is operational
acceptance evidence, not an isolated causal percentage saving from sharding.

Deployment remains gated by one successful same-repository main-push CI
conclusion and a tested-revision check. The temporary proof never exercised that
deployment path. The root coordinator recorded Jira acceptance comment 10410
and verified the KAN-69 transition to Done after this evidence was reconciled.
