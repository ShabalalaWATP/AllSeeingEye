# Research allowance API

Research allowances count accepted research runs, including subscription editions.
They are separate from AI provider-call and token policies. See
[research tiers](../AI_COST_CONTROLS.md#research-tiers) for operator guidance.

All paths use the `/api` prefix. Responses are private and are not cached.
Timestamps are ISO 8601 UTC. No endpoint changes a model assignment or account role.

| Method and path | Access | Result |
| --- | --- | --- |
| `GET /api/research-usage/me` | Signed-in account | Its research allowance and current usage |
| `GET /api/admin/research-usage` | Administrator | The four tier definitions and account allowances |
| `PUT /api/admin/users/{user_id}/research-tier` | Administrator | Assign a tier using the expected current revision |

An allowance contains `tier`, `label`, `limit`, `period`, `used`, `remaining`,
`period_start`, `resets_at` and `revision`. Administrator account entries also
contain `user_id`. The administrator list returns `tiers` and `items` arrays.

Assignment input is `{ "tier": 1, "expected_revision": 0 }`. Tiers are integers
from 1 to 4. An account without an explicit assignment has Level 1 and revision
zero. A stale revision returns HTTP 409; clients reload before offering another
save. Changing a tier preserves usage already recorded in both periods.

Only administrators can change tiers, including their own. Assignment rechecks
current administrator authority under the account locks and records an audit entry.
It does not permit self-deactivation, a role change or editing another account's
usage counters.

Admission refuses exhausted research with HTTP 429 and error code
`research_usage_limit`. Its message explains the allowance and reset. Clients must
retain this explanation rather than display a generic rapid-request warning.
Requests rejected before admission do not consume a run. Existing-job retries,
resumes and idempotent submission replay do not consume another run.
