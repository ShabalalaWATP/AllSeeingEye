# KAN-229: explicit Brief settings route inventory

Date: 10 October 2026.

Hosted CI at `212299ff` reported 353 routes against the independent oracle's
352-route baseline. KAN-229 adds one endpoint:
`PUT /api/schedules/{schedule_id}/brief-settings`. Its original 94 router owners
remain unchanged on this standalone branch.

The fixture now requires that exact owner/method/path tuple and a fixed total of
352 plus one route. Existing overlap-order, reverse-name, full OpenAPI,
endpoint/dependency metadata and HTTP matching assertions remain intact.
The expected inventory is explicit, not derived from production at runtime.

All six router contract tests passed in 14.41 seconds. Scoped Ruff and formatting
passed. Coverage was not measured. No production source or acceptance threshold
changed. The combined branch has a separate inventory for its additional idle
activity and enquiry endpoints.
