# KAN-71: retain acquisition guards without a duplicate warm compilation

## Scope and control-flow proof

The ordinary PostgreSQL fixture compiled the complete schema fingerprint twice
in succession when its worker already had a sealed template. The initial check
remains fresh on every acquisition. The second check now runs only after the
first template has been created, populated, disposed and sealed.

`TemplateWorker` directly inherits `object`; its template and fingerprint are
ordinary instance attributes. On the warm path, the only operation between the
two previous fingerprint calls was the false `template is None` condition.
There was no await, lock, descriptor, allocation or callback between them. The
ordinary pytest fixture drives one acquisition with `asyncio.run` before app
setup; xdist workers use separate processes.

The cold path still checks after all awaited initialisation and the existing
template assignment. A changed schema or DDL listener rejects cloning while
retaining the owned template for cleanup. Prepare/teardown revalidation, native
ownership, cancellation acknowledgement, sealed-template connection refusal,
transaction behaviour, authentication and coverage gates are unchanged.

This preserves the observation boundaries of the existing cooperative fixture.
It introduces neither cross-call caching nor a thread/signal atomicity guarantee.

## Correctness and selection

- The new first/warm regression failed before the change because a second warm
  compilation occurred; the other eleven new cases already passed.
- All 61 focused acquisition, lifecycle, fingerprint and guard cases pass after
  the change. They cover metadata and DDL-listener changes during each of CREATE,
  schema creation, disposal and sealing, plus rejection before warm allocation.
- All 12 native PostgreSQL cases pass, including three new regressions for cold
  rejection, warm rejection and a change during native cloning. The latter
  verifies the physical column definition is rebuilt by prepare and remains
  subject to mandatory teardown even after metadata is restored.
- The native run records two ordinary clones, zero fallback and ten cases using
  their explicit native fixtures. Its complete database catalogue is restored;
  all durability settings are on and its owned service is acknowledged removed.
- Collection retains all 2,886 cases selected by the previous complete CI and
  all 2,363 older retained IDs. It adds only the three native guard cases to the
  PostgreSQL selection, giving 2,889 selected cases from 11,073 collected cases.
  The twelve new in-memory unit cases do not replace any native assertion.

Independent quality and security reviews of the exact helper and regressions
found no actionable issues. The native evidence was independently audited.

## Controlled local comparison

The separately reviewed protocol freezes full Git `7f124652` for the control
and replaces only the reviewed helper bytes in the candidate. Both contain
5,734 tracked files. The two new regression modules are excluded from both timed
archives, with their hashes retained separately. All original tests, production
sources, locks and admission guards are identical.

The fixed order is control, candidate, candidate, control, with the same 105
original eligible cases, four workers, zero worker replacements, real branch
coverage and authentication. Each arm has a fresh durable pinned PostgreSQL
service, two CPUs, 2 GiB RAM and 2 GiB tmpfs. Each uses the same excluded catalogue
warm-up in a separate process and a two-second cooldown. No profiler or replaced
application/fixture function runs during measurement. Each pytest process has a
450-second bound; failed or unmatched observations are retained.

The single predeclared campaign completed with no retries or discarded arms:

| Fixed arm   | Covered subprocess wall time |
| ----------- | ---------------------------: |
| Control 1   |                155.0628475 s |
| Candidate 2 |                152.9960589 s |
| Candidate 3 |                152.3147329 s |
| Control 4   |                155.9675563 s |

Control median: **155.5152019 s**. Candidate median: **152.6553959 s**.
The observed local saving is **2.8598060 s**, approximately 1.84%, with only two
observations per variant. This does not predict a whole-CI improvement.

All 420 measured cases and four excluded warm-ups pass. Every measured arm has
105 clones, zero fallback and zero ineligible cases. The four production branch
arc sets are identical, containing 99,957 arcs across 1,578 files each. This is exact branch-arc
parity, not an aggregate coverage percentage claim. All source/runtime seals,
full catalogue comparisons, durability checks and acknowledged owned-resource
cleanup pass. The original launcher exits zero and records four completed arms.

Independent quality and security auditors reconciled the original case IDs,
1,272 successful phase records, raw SQLite coverage and JSON exports, source
archives, interpreter/dependencies and cleanup. Both accepted the retained
evidence with no actionable discrepancy. The conclusion is limited to this
fixed local comparison, not statistical or whole-CI acceptance.

## Remaining acceptance

The last complete CI, [run 37034703344](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/37034703344),
passed at `7f124652`. Its four PostgreSQL jobs plus merger used 2,773 seconds,
46.2167 runner-minutes. That remains above KAN-71's 30-minute requirement. This
local helper change needs a fresh complete CI after publication. Five comparable
before and five after measurements remain required once a qualifying complete
run exists; neither local attribution nor this bounded comparison establishes
the whole-CI target. No release merge or ticket completion is claimed here.
