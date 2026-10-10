# KAN-216: route contract fixture reconciliation

Date: 10 October 2026.

The independent router oracle predated the idle-activity endpoint, enquiry
routers and Brief settings editor. Hosted CI correctly reported the obsolete
94-owner/352-route inventory. Each branch now lists its reviewed additions
explicitly and retains a fixed expected count. The expectations are not derived
from the production router at test runtime.

| Branch ticket | Owners | Routes | Added contracts |
| --- | ---: | ---: | --- |
| KAN-166 | 95 | 354 | Activity and public enquiry submission |
| KAN-167 | 96 | 358 | Activity, public enquiry and four administrator enquiry operations |
| KAN-169 | 96 | 358 | Same contracts as KAN-167 |
| KAN-220 | 95 | 354 | Activity and public enquiry submission |
| KAN-232 | 95 | 354 | Activity and public enquiry submission |
| KAN-231 | 94 | 354 | Activity and Brief settings editing |
| KAN-216 integration | 96 | 359 | All seven additions above |

Only the fixture inventory changes. Existing overlap-order, reverse-name,
complete OpenAPI, endpoint/dependency metadata and HTTP matching assertions
remain intact. An independent source review checked all six materialised
variants against their actual route declarations and found no missing checks.

Validation: all six router tests passed independently on each of KAN-166,
KAN-167, KAN-169, KAN-220, KAN-232 and KAN-231. The integrated branch passed all
46 selected cases covering the router contract, migration startup imports,
upload sessions, expiry after session closure and transactional token claims.
Scoped Ruff, formatting and diff checks passed. These groups overlap; they are
not an overall test-suite count. Coverage was not measured in these runs.

The KAN-182-only fixture has a separate record because it contains just the
activity endpoint. Final hosted CI remains required after propagation.
