# KAN-169 route inventory fixture repair

Checked on 10 October 2026 against KAN-169 base `b4faee1d`.

## Failure and branch inventory

The independent registration oracle still described the public-site baseline of
94 owners and 352 routes. KAN-169 now has 96 owners and 358 routes. The local
baseline failed the owner-count assertion before checking the route total.

The six additions are explicitly recorded by owner, HTTP method and path:

| Owner | Method | Path |
| --- | --- | --- |
| `auth` | POST | `/api/auth/activity` |
| `enquiries` | POST | `/api/enquiries` |
| `admin_enquiries` | GET | `/api/admin/enquiries` |
| `admin_enquiries` | GET | `/api/admin/enquiries/{enquiry_id}` |
| `admin_enquiries` | PATCH | `/api/admin/enquiries/{enquiry_id}` |
| `admin_enquiries` | DELETE | `/api/admin/enquiries/{enquiry_id}` |

The reference include order now contains the two enquiry owners. The test still
requires exact owner uniqueness and membership, and checks every overlapping
path-family and endpoint-name ordering edge. Exact OpenAPI, reverse lookup,
endpoint metadata, method matching, redirects and missing-path comparisons are
unchanged. No runtime registration was changed.

## Propagation

Do not copy this branch's counts blindly. GitHub Actions run `38008488527`, job
`114082737714`, was on KAN-231 head `7c913b7be333d42bd4f87cc26bfedf54030f022c`.
That branch has 94 owners and 354 routes: it includes `POST /api/auth/activity`
and `PUT /api/schedules/{schedule_id}/brief-settings`, but neither enquiry owner.
The latter endpoint is absent from this KAN-169 branch. An integration containing
all three features must explicitly reconcile its own endpoint inventory.

## Validation

The stale 94-owner assertion reproduced locally before the repair. All six route
tests then passed as part of the following 33-test run in 21.35 seconds:

```text
python -m pytest tests/test_input_declarations.py tests/test_research_input_api.py tests/test_research_input_sessions.py tests/test_router_order.py -q --no-cov
```

The shared input session fixture repair in that run is a separate commit. Ruff
lint, Ruff format verification and `git diff --check` passed. Coverage was not
measured for this test-only repair. No production code, workflow, threshold or
security scanner was changed.
