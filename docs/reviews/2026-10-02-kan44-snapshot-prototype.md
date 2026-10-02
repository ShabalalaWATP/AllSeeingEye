# KAN-44 snapshot restoration prototype

This prototype starts from `13e9525d904e744e0bc7ea329e8d475234f86f25`.
It removes temporary generators and repeated decoder construction while retaining
the public event representation, validation and store limits. No dependency,
snapshot format, migration, configuration or retention policy changes.

## Evidence and scope

A controlled diagnostic used the unchanged production image and the same signed
100,000-event snapshot as the completed restart comparison. Three fixed samples
preserved full event contents, ordered IDs and load-once behaviour. The snapshot
and six source witnesses matched before and after each sample. Actual non-root
read-only admission and cleanup were checked. Two earlier zero-sample fixture
preflight failures remain recorded separately.

The diagnostic included profiler overhead. Median cumulative costs included
0.456 seconds in provenance validation, 0.683 seconds in byte estimation and
0.116 seconds in 100,002 decoder constructions. These costs nest and must not be
added or treated as measured savings. The earlier delivered-main restart result
did **not** meet the existing six-pair conservative three-second requirement.

The prototype changes three bounded responsibilities:

- Provenance validation uses explicit element loops, keeping tuple, length and
  member checks in their original order, with the same error. Every `Event`
  constructor still invokes validation.
- Byte estimation expresses the same twelve text contributions directly and
  iterates attributes and tags without temporary generators. Complex evidence
  and provenance contributions, overheads and accounting units remain unchanged.
- Each snapshot read owns one strict JSON decoder. UTF-8 decoding, leading BOM
  rejection, whitespace and extra-data behaviour, forbidden constants, signatures,
  gzip completion and file/record limits remain unchanged. No decoder is shared
  between reads or threads.

## Correctness checks

All 96 new companion contract cases passed against the unchanged predecessor
before production edits. They cover direct and nested provenance validation,
exact byte contributions and eviction boundaries, signed JSON rejection versus
invalid-record skipping, and repeated/concurrent reads. Rich-event accounting is
pinned to the predecessor's 7,512-byte total and individual complex contributions.

After the changes, the focused snapshot, store, cooperative work, source-date and
evidence consumers passed: **301 passed, one skipped**. The skip is the existing
symbolic-link case on a Windows account without link-creation capability. These
checks used a private frozen environment with Python 3.13.3 and no inherited
`ASE_` variables. They are correctness evidence, not Linux performance evidence.

Scoped Ruff, formatting and whitespace checks passed. Strict mypy passed across
1,578 source files; all three import contracts and scoped Bandit checks passed.
Independent code-quality
and security reviews found no actionable issue in the exact three-file change
and companion tests. Coverage was not measured in the local focused runs. All 38
hosted checks passed at the measured source commit `2ffe17a4`.

## Uninstrumented comparison

The fixed comparison completed on 2 October 2026, using baseline `13e9525d` and
candidate `2ffe17a4c70121cb0a23724a0cd727b1e7a1e321`. Complete Git archives and
1,962 installed runtime source/configuration files per image matched their frozen
revisions. Both supported production images had identical Python 3.13.15,
74-package, OS and Debian inventories, with identical effective environments.
The canonical signed 100,000-event fixture and non-root, read-only, offline
resource controls were unchanged. No provider credentials or live data were used.

All fourteen observations completed: two retained excluded warmups, then three
fixed ABBA blocks. No retry, invalid observation or sample substitution occurred.
Each restored exactly 100,000 events with zero skipped, identical full content,
ordered IDs, category/date statistics and 156,755,560 estimated bytes under the
536,870,912-byte budget. Load-once behaviour, disposal and source/fixture hashes
also agreed. Both preflights confirmed non-root reading and actual `EROFS`
write-open rejection. The primary interval covered complete snapshot loading,
without cProfile or import instrumentation; app construction was outside it.

The six directional paired load improvements were 0.244074438, 0.294639323,
0.344265109, 0.293447615, 0.294984772 and 0.308235103 seconds. Their median was
**0.2948120475 seconds**, with an inclusive IQR of 0.01117697825 seconds. All six
passed the predeclared positive-beyond-timer-granularity consistency screen.
This is not a statistical confidence bound or a per-change attribution.

Twenty offline protocol checks passed. The exact harness, actual prepared inputs
and completed raw evidence received independent quality and security reviews,
with no actionable findings. All 84 commands stayed within their bounds.
Collection took 164.009082 seconds within the 300-second cap; cleanup took
1.2675404 seconds. The final owned container, volume and error lists were empty,
with no unresolved operation. Images and evidence remain retained as artefacts.

Private evidence is retained in
`C:/Users/alexo/.codex/worktrees/kan44-snapshot-restore/comparison-20261002`.
The primary `report.json` SHA256 is
`4c37c7a069457dc0ea045d06c41e9a7a71b82b7f23db5375c3f125ab6f6a8a93`.
Raw observations, source/image manifests, input seals, admissions and cleanup
records support that report; the earlier failed fixture attempts remain intact.

These isolated load savings do **not** establish the remaining three-second
SIGTERM-to-first-ready acceptance. KAN-44 remains open, the PR remains a draft,
and any further candidate or full restart comparison needs its own reviewed
scope and controlled evidence.

## Optional Web Push imports

A subsequent bounded change defers the delivery adapter import until the existing
key, contact-subject and cipher-availability guard permits sender construction.
The request service still constructs its real endpoint validator on first use.
Configured key parsing, public-key derivation, worker execution, persistence,
current-session authorisation, transport and cancellation behaviour are unchanged.
Only `container/web_push.py` changes production code in this follow-up. There is
no language or document-adapter change and no key-rotation work.

Before the fix, the fresh-process ASGI/idle-worker import regression failed as
expected because `pywebpush`, `py_vapid` and the delivery adapter were loaded.
The other eight new contract cases passed. After the fix, the focused push API,
transport, scope, concurrency and startup consumers passed: **37 passed, one
skipped**. The skip is the existing PostgreSQL race parameter, which requires
`ASE_NOTIFICATION_POSTGRES_URL`; the private SQLite race passed. No shared or
external database was used. A final strengthening of the cold request-validator
check passed all nine companion cases, including unconditional worker join and
container disposal on failure paths.

Ruff, formatting, whitespace and scoped Bandit checks passed. Strict mypy passed
1,578 source files and all three import contracts passed. Independent quality and
security reviews found no actionable source issue. The tests preserve real
configured public-key construction, invalid-key errors before delivery admission,
unavailable guard combinations, endpoint rejection and worker cancellation.

The Web Push follow-up has **no measured performance result**. The snapshot
comparison above remains attributed only to immutable commit `2ffe17a4`; its
0.2948-second median must not be added to instrumented import costs or assumed to
apply to this later candidate. Any complete restart comparison requires separately
reviewed frozen inputs and the unchanged conservative acceptance criterion.

## Complete restart result for 719d7e11

The subsequent fixed reference-host campaign compared historical release
`1d924272` with the unmerged snapshot and Web Push candidate `719d7e11`.
All fourteen observations completed: two retained excluded warmups followed by
three ABBA blocks, without retries or discarded samples. The supported releases
used their real schema and dependency graphs, with 61 common package versions
and thirteen additional candidate packages. This is a complete-release
comparison, not isolated attribution to either optimisation or production downtime.

All six conservative improvements were 2.640197706, 2.996846286, 2.904568182,
2.915817062, 2.439129449 and 3.016279307 seconds. **Only one of six meets the
predeclared three-second requirement, so the target remains unproven.** The raw
median was 3.2225701395 seconds; it does not override the conservative bounds.

Every initial and replacement process restored 100,000 events. Full content,
ordered IDs, real readiness, migration heads, source/image identities, numeric
phase values and lifecycle witnesses agreed. Actual migration imports were
1,429 for the historical baseline and 199 for the candidate. Independent quality
and security audits recomputed the raw results and found no evidence discrepancy.
All 1,226 commands were bounded, with no retries or unresolved operation; the
final owned container, volume and error censuses were empty before completion.

Private evidence is retained in
`C:/Users/alexo/.codex/worktrees/kan44-snapshot-restore/restart-candidate-20261002`.
The report SHA256 is
`b8ae5ceededd8ce1c971b440f20295e9c8cc566014daf8425faa7168d88b6b6c`.
The earlier isolated comparison and negative restart campaigns remain unchanged.

A single-process Docker bootstrap was assessed but not implemented. Its possible
import reuse has no measured benefit, and migration-phase PID1 signals, repeated
stops during engine disposal and Uvicorn's import/handler handover require
additional lifecycle work. The existing launcher and standalone CLI are unchanged.

## Strict collection decoding follow-up

The retained attribution profile identified generator setup and resumption for
100,000 point records and empty tag/transformation collections. The next small
candidate validates the two numeric coordinates directly for exact built-in
lists and returns empty immutable collections after the existing type and size
checks. Container subclasses retain the original iteration behaviour. Non-empty
tags and transformations still follow their original validation paths, including
every `Point`, `TextTransformation` and `Event` constructor. JSON decoding, HMAC,
file limits, invalid-record skipping, memory accounting and retention are unchanged.

New companion cases and existing snapshot/provenance checks passed against the
unchanged predecessor: **112 passed, one existing Windows symlink skip**. An
initial test fixture incorrectly assumed the shared event builder had empty tags;
the fixture was made explicit before production edits. Subsequent checks,
including the added container-subclass regression and store/service consumers,
passed: **225 passed, one existing Windows symlink skip**. Scoped Ruff, formatting,
mypy, Bandit and whitespace checks passed. These are correctness checks only;
coverage and performance were not measured for this follow-up.
Independent quality and security reviews found no actionable issue in the exact
two-file production change and companion tests, including the preserved subtype
behaviour. The next proposed acceptance comparison uses the complete restart
path and the same six-pair conservative threshold, subject to its separate frozen
source, harness and prepared-input review gates.
