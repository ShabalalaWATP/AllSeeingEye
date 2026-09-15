# Research and Subscriptions acceptance record

This is a live release record for the [approved implementation plan](../../RESEARCH_SUBSCRIPTIONS_IMPLEMENTATION_PLAN.md). A local synthetic test pass is evidence for a software contract, not evidence that a live source is current or that an analytical judgement is true.

## Code snapshot and environment

- Date: 14 September 2026. Working branch: `main`, baseline commit `fb2a591`; another concurrent camera task advanced HEAD to `b79272b` during this work. Research/Subscriptions implementation changes remain uncommitted; no production deployment or operator database migration has run.
- Backend tests use process-local `ASE_DATABASE_URL` and `ASE_TEST_DATABASE_URL` overrides pointing to disposable in-memory SQLite. A populated PostgreSQL upgrade and concurrent-session acceptance have not been run.
- The frontend API schema and generated types were refreshed after the baseline-acceptance and administrator diagnostic routes were added.
- No live provider or configured model has been called for this acceptance record. Credentials previously supplied in chat are not recorded here.

## Checks observed so far

| Check | Result | Scope and limit |
| --- | --- | --- |
| Backend baseline collection/depth/replanning | 55 passed | Initial snapshot, no coverage measurement |
| Source allocator/collection/composition | 63 passed | Explicit-term ranking and current capability allocation |
| Feed HTTP/credentials/bounds/research | 107 passed | Includes timeout classification and safe errors |
| Radar/ONS source and research composition | 85 passed | Offline adapter contracts, no live licence or endpoint acceptance |
| Legacy report API regression | 5 passed | Synthetic headlines now correctly require review without original passages |
| Fresh-web report HTTP regression | 1 passed | Discovery context is frozen but zero evidence abstains before drafting |
| Focused subscription UI regressions | 20 passed | Four files, controls and baseline history |
| Frontend typecheck and production build | Passed | Build has existing large-chunk advisories |
| Research replan and replay regression | 34 passed | Unavailable source no longer receives an identical second-pass query |
| Exact-edition comparison integration | 40 passed | Disposable SQLite and API/history tests; no semantic adjudication claim |
| Staged brief and preset UI | 29 passed, plus 6 preset rerun | Focused component tests, TypeScript, ESLint and Prettier |
| Synthetic evaluation contracts | 60/60 cases and 194/194 checks | No human-reviewed labels or live model calls |
| Research/Subscriptions frontend group | 508 passed across 105 files | Fresh run after stale-fixture correction and exact-version Ask Eye UI integration |
| Frontend full suite | Not passed as a gate | A full run was interrupted after two camera integration failures outside Research/Subscriptions |
| Backend full suite | Not passed as a gate | Earlier run was interrupted during concurrent edits |
| Alembic graph and additive migrations | One head `0044`; archive adjacent suite 27 passed, source-review 21 focused passed, ledger migration in focused suite | Disposable SQLite only; no operator database migration or PostgreSQL upgrade |
| Exact-version Ask Eye backend API | 32 passed | Exact-version reader and final release checks |
| Exact-version Ask Eye frontend | 17 focused passed in the saved/report/assistant/API slice | Report-scoped chats can be saved and resumed with the exact edition; browser acceptance and broader entity/relevance work remain |
| Original-passage retention cleanup | 12 passed | Includes disposable SQLite deletion/worker regression; no PostgreSQL result |
| A05 tier synthesis | 89 focused passed | Basic/Deep/Advanced limits and structural requirement coverage; whole-stage budgeting remains |
| X03 forecast/indicator core and persistence | Earlier 77-case domain run; latest 84-case combined ledger run after security fixes | Exact reviewed-claim anchoring and unknown readings; post-issue outcome evidence, numerical readings and UI remain |
| Settled report/doctrine/ledger integration | 58 passed across nine focused backend files | Disposable SQLite; includes selected source snapshot, final doctrine and ledger routes |
| Frontend contract integration | 12 tests across four affected files and typecheck passed | OpenAPI and TypeScript regenerated after `0044` and selected-source reader/export routes |
| Frontend typecheck, lint and production build | Passed after Ask Eye integration | Build reports existing large-chunk advisories; authenticated browser journey not yet run |
| Schedule archive and recovery | 27 adjacent tests passed | SQLite foreign keys, history retention, pause/resume fences and due fairness; PostgreSQL unverified |
| A01 source reviewer history and reader/export bridge | 21 focused history tests, 35 related reader/export regressions passed | Opt-in selected snapshot does not alter frozen judgements or item grades; automatic production scoring and reviewer UI remain |
| A02 final doctrine gate | 29 focused passed | Post-draft changes revalidated before release; typed forecast and exact-passage fields are not yet available in production packet |
| A04 ambiguous claim comparison | 46 focused passed | Swapped/reidentified claims require review rather than definitive assessment; semantic verification remains |
| E05 challenge receipt recovery | 8 focused passed | Lease-fenced selected source results and charge survive restart; broader challenge coverage remains |
| Backend Research/Subscriptions integration | 133 passed across 17 focused files | Disposable SQLite; full backend suite was stopped after very slow progress and is not a pass |
| Authenticated browser smoke | Login, Research and Subscriptions loaded on isolated 8015/5175 services | Disposable QA user and SQLite; no paid model call, full keyboard/mobile/export journey or production service acceptance |
| Subscription archive and paused-copy UI | 15 focused tests across copy, refresh and brief-workspace files passed | Controls describe retained-history archive semantics; ordinary and exact-revision brief subscriptions can be copied without an immediate run; live schedule execution remains |
| Backend static checks | Ruff, strict mypy across 1,140 files, import layering and format passed after ledger/source projection; Bandit passed after narrow reviewed annotations | Full-suite and independent review gates remain |
| Frontend dependency audit | Passed after locking `js-yaml` 4.3.2 | Initial high-severity transitive advisory resolved; recheck after future dependency changes |
| Backend dependency audit | Passed for published dependencies | Local `ase` package is not on PyPI and was skipped by pip-audit |

Additional focused results and exact commands are recorded in [EXECUTION_LOG.md](EXECUTION_LOG.md). Coverage figures reported there apply only to named modules or fixture suites, not the full product.

## Quality and operational gates

| Gate | State | Evidence still required |
| --- | --- | --- |
| Deterministic evaluation corpus | Implemented offline | Independent human labels and live-model quality runs remain separate gates |
| Human-reviewed analytical quality | Unverified | Independent reviewer labels, disagreement record and current-model runs across six domains/depths |
| Exact original passages in production reports | In progress | Guarded selected retrieval and exact-version read are implemented, but current reviewed source policies, multi-requirement mapping and correction governance remain |
| Subscription corrections and long-interval coverage | In progress | Retained selected index wired to collection, source cursors, limits, outage and annual interval tests |
| Material-change classification | In progress | Exact-version projection and history UI pass; semantic ambiguity handling and notification policy remain |
| Live source capability | Unverified | Minimal read-only current request per configured route with timestamp, status, count and limitations |
| Current model and budget | Unverified | Authorised bounded runs, stage and usage receipts, quality assessment |
| PostgreSQL migration and concurrency | Unverified | Disposable populated upgrade, repeated upgrade, race and restart checks |
| Browser journeys and accessibility | In progress | Isolated authenticated desktop Research/Subscriptions smoke passed; narrow, keyboard, reduced-motion, creation and report-reading journeys remain |
| Word/PDF/Markdown rendering | Unverified | Normal, review and partial/quiet reports rendered and visually inspected |
| Security and dependency checks | In progress | Focused review found original-passage, subscription deletion/history, ledger expiry and head-binding gaps, fixed with regressions. Dependency audits and Bandit pass; full diff review/CI remain |

No quality percentage, source coverage percentage, or calibration claim is released from this record. Current automation remains review-required wherever source context or required checks are missing.
