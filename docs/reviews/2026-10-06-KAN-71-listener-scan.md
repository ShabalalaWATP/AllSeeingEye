# KAN-71 listener allocation milestone

Ordinary PostgreSQL template eligibility still recompiles the complete current
DDL and checks every metadata, table, column, constraint, index and type listener
on each fingerprint call. The scan now avoids allocating tuples only for exact
pinned `_EmptyListener` and `_ListenerCollection` classes whose traversed backing
containers are exact built-in `deque` instances. Any joined listener, unfamiliar
class, subclass or altered storage retains the original complete tuple iteration,
including callback detection and iterator exceptions. There is no schema cache.

## Review and regression evidence

The original implementation passed 40 focused cases and failed four intended
iteration-budget cases. Its first optimisation passed 106 cases, but security
review found that an exact joined collection could wrap unfamiliar storage with
zero length and a non-empty iterator. That clearance is superseded; the candidate
was repaired before integration or release.

The corrected nested matrix reproduced 30 genuine failures against the preserved
first candidate: 15 incorrect admissions and 15 missing iterator exceptions.
Four earlier fixture construction errors are separately retained. The repaired
suite passed 136 focused cases in 1.80 seconds. Ruff, formatting and whitespace
checks passed. The unchanged complete fingerprint algorithm serves as the oracle
for real metadata changes, restoration and compiler failures. All fresh DDL and
fixture/acquire/lifecycle guards outside the allocation scan remain unchanged.
Both exact repair reviews are clear. Files contain 140/140/261 lines.

Repair review manifest SHA256:
`a5bf63c3d3cc0ddfe06bcfde06c11d990ab8182ee3bb4ec56f595bf97a07b4ce`.
Full source patch SHA256:
`e280ece3d221ff050ff4ea44700e7438c76522817547e2952a09523e0dbd40a7`.
Result SHA256:
`356900ae25379bebbea101298c120c021c3094652d06fb510bc0435f8b5e5f72`.
Private evidence under `kan71-listener-scan/evidence/v1` and `v2` preserves the
failed first candidate, its source snapshots and every relevant check receipt.
No private runtime or evidence files are committed.

## Limits

This change affects test eligibility allocation only. It has no native PostgreSQL
performance or new coverage measurement. The earlier successful 65-case native
diagnostic predates this patch; its timing must not be relabelled as a result of
the optimisation. Current d078 whole-CI PostgreSQL cost was 49.58 runner-minutes,
above the 30-minute criterion. Fresh published-head CI and the required before/after
observations remain outstanding. KAN-71 remains open.
