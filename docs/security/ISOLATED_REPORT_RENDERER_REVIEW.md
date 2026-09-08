# Isolated report renderer review

8 September 2026. Independent read-only review of the candidate renderer identified
three required repairs. This records findings, not completed runtime acceptance.

1. Failed descendant cleanup must not release capacity or remove the workspace
   while processes may still be alive. Quarantine resources until absence is
   established, or stop further renderer admission. Test genuinely unconfirmed
   descendants, not a fixture that kills them before raising cleanup failure.
2. Validate PDF metadata types and values. pypdf BooleanObject(False) is truthy
   under generic Python object truth testing; presence of StructTreeRoot alone
   also accepts null or invalid structures. Reject false/null/malformed cases.
3. Bound aggregate writable job storage. A final PDF size check and memory/PID
   cgroup limits do not bound a host temporary-directory bind mount. Require a
   supported per-job filesystem/storage limit or refuse that runtime policy.

The implementation owner repaired these findings with focused regressions:
unconfirmed cleanup now quarantines the worker and retains its admission slot;
PDF admission checks explicit Boolean and structure types; writable browser data
is confined to size-limited private tmpfs mounts. The expanded compatibility and
release group passed 55 tests. A subsequent malformed-structure regression first
reproduced five invalid acceptances, then the final renderer/worker/admission
group passed 35 tests after checking ParentTree array types and StructElem children.
Ruff, mypy (632 source files), both import contracts and file-length checks passed.
Independent final read-only review found no further blocking defects within the
inspected implementation and final typed-structure repair. It confirmed resource
quarantine, bounded writable tmpfs, output framing and post-render access checks.
The checks are shallow PDF admission, not complete number-tree/MCID consistency
validation or PDF/UA certification.

The main merge preserved SEC/provenance rendering and passed 55 focused renderer,
document API, structured HTML and final-release tests in 99.42 seconds. Whole
source mypy passed for 653 files. The first test invocation referenced a missing
test filename and collected no tests; the corrected invocation produced this
result. Feature hooks passed before the merge; no production runtime was enabled.

The previous controlled-worker tests establish only their tested subprocess and
legacy-export behaviour. No real Linux isolated browser deployment, native-speaker
review or PDF accessibility certification has been completed. An offline desktop
Chrome diagnostic, if performed, will be reported separately as HTML/font output
evidence and will not validate this isolation policy.
