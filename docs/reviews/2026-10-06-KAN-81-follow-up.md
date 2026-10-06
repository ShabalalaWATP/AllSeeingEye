# KAN-81 follow-up evidence, 6 October 2026

PR #132 merged as `037f2d760467aac3b6ff77e378b62e7f9f684bf3` at
18:36:38 UTC. CI `37510020691`, CodeQL `37510015490` and image SBOMs
`37510020323` passed on its reviewed head `df209541`. Main CI `37512638756`,
CodeQL `37512638036` and SBOMs `37512638308` subsequently passed. Automatic
deployment `37514287368` passed at 18:52:09 UTC. The first subsequent public
health and readiness probes both returned 200 with verified TLS and no redirect.
Read-only SSH confirmed a clean checkout at the merge, one healthy API, healthy
parser and running web images labelled with that revision. The healthy database
container retained its original 25 September identity.

Reference run `37510041260` completed one valid baseline/candidate pair.
Candidate source was `e412348d1fa4ef0cfb90255eba67a923b4188e9a`, frontend tree
`99a185f5f78352591730d2126bcb3eb678a7c60d`. Independent reconciliation verified
source, input, artifact and owned-command identities. Only controls met both
limits; the combined target remains false.

| Phase            | Baseline median/max, ms | Candidate median/max, ms |
| ---------------- | ----------------------- | ------------------------ |
| New records      | 37.61 / 65.71           | 35.36 / 56.59            |
| Existing records | 27.94 / 34.73           | 22.66 / 30.01            |
| Mixed records    | 38.31 / 60.82           | 33.35 / 39.96            |
| Controls         | 22.02 / 34.29           | 19.01 / 27.90            |

This single pair establishes neither causality nor repeatability. It does not
replace real-browser acceptance. Earlier negative pairs remain retained.

The private Edge v16 attempt failed with only the 40 bootstrap frames, before
any timed phases. The root trace started 32.716 seconds after the operator
claim and lasted 3.393 seconds. The acknowledgement helper accepted no
acknowledgements and timed out on its second TCP connection. Its receipt cannot
establish the request method or transport stage. Neither application latency
nor an origin-check failure is inferred from that timeout.

All owned applications, jobs and listeners closed; the API required the owned
job fallback. The trace stream and owned browser tabs closed. Failed receipts
and trace bytes remain private. The trace has no reported data loss, but the
attempt is incomplete and supplies no performance acceptance evidence.

The next browser procedure is prepared before starting the controller clock.
Transport-stage diagnostics are being prepared without relaxing the timing,
origin, isolation or admission limits. KAN-81 remains In Progress.

## Empty news-query follow-up

The next change checks category and exact source constraints first, then returns
true for an empty trimmed query before constructing searchable text. Non-empty
queries retain the same searchable fields and locale-aware comparison. It does
not change filtering order, record identity, hook dependencies or expiry.

On unchanged production, two empty/whitespace regression tests failed with four
text-field reads instead of zero; fourteen compatibility tests passed. After the
fix, 54 tests passed across eight files, including selection integration,
clock-only expiry and scoped corrections. These checks ran alongside the
isolated collection census and provide correctness evidence only. No latency,
coverage or completed KAN-81 acceptance is claimed for this change.
