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
and no new production merge or release has been approved. Any further candidate
or full restart comparison needs its own reviewed scope and controlled evidence.
