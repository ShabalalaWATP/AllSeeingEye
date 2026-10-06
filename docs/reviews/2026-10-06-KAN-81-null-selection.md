# KAN-81: skip scans when no item is selected

Four globe paths searched loaded records even when the selection was null.
The dashboard hook, observation controls and hazard/fire filter effects now
return the same empty selection without traversing IDs in that case. Non-null
IDs, including an empty string, still use the original lookup.

Three regression files cover traversal, replacement object identity, filtered
selection, expiry, mirror lag and workspace/authentication invalidation. The
unchanged production baseline produced four expected failures, each reading
64 IDs instead of zero, and 13 compatibility passes. After the guards, 62 tests
passed across 13 files. Both TypeScript configurations, focused ESLint,
Prettier and git diff checks passed. No coverage or latency result was measured.

Independent quality and security reviews cleared the seven source files at
manifest `3e5d54c09dcfdd9920377d3ce69db7b2254734b3582cf6dd7584b336b6b2ac56`
and patch `516484be49061cc8a55d76e9d20ee472e4dd679c5afd5ee413e05f1787cb8e24`.
All seven owned commands closed with empty final jobs and closed handles.
One successful TypeScript process was still present in its job before owned
closure, so natural process-tree emptiness is not claimed for every command.

KAN-81 remains open. The last valid Linux observation, run 37497054952,
measured candidate median/max totals of 40.21/62.70 ms for new records,
24.02/32.98 ms for existing records, 34.10/46.17 ms for mixed records and
20.07/26.90 ms for controls. Its target result was false. These measurements
predate the null-selection change. A fresh immutable observation and completed
browser capture are required before claiming an improvement or acceptance.

PRs #130 and #131 were squash-merged as 0c180576 and 1a84156c. Main CI and both
automatic deployments passed. The second release initially returned readiness
503 at 17:17:19 UTC and returned health/readiness 200 at 17:18:22 UTC; the cause
is unknown. Read-only SSH confirmed a clean production checkout at 1a84156c
and a healthy single API container. The database container was unchanged.

Private Edge v14 authenticated the ordinary synthetic user, rendered the globe
and bootstrapped all five admitted layers to 1,000 records each. Its separate
acknowledgement helper rejected its first GET before the driver or trace began.
No performance capture is claimed. The native applications stopped normally,
all owned jobs and handles closed, and postflight listeners were absent. Failed
helper and incomplete capture receipts remain retained for diagnosis.
