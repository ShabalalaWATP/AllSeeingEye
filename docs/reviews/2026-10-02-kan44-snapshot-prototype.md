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
1,578 source files; all three import contracts and scoped Bandit checks passed. Independent code-quality
and security reviews found no actionable issue in the exact three-file change
and companion tests. No coverage percentage or performance improvement has been
established here.

## Next measurement gate

A separately reviewed uninstrumented comparison must freeze the full original
and candidate source manifests, supported production images, equal dependency
inventories, fixture bytes and environment. The proposed sequence retains two
excluded warmups followed by three fixed ABBA blocks, giving six adjacent paired
effects. Fourteen fresh containers share the same non-root, read-only, offline
resource controls and a 300-second collection cap. Failed/invalid observations
must remain recorded without retries or selection.

The primary outcome is complete snapshot load duration. Content, ordering,
estimated bytes, retention and lifecycle must remain identical outside timing.
Local load improvements cannot establish restart acceptance. KAN-44 remains open
until its complete acceptance criteria and authorised delivery workflow are met.
