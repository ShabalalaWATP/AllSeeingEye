# KAN-182 route inventory reconciliation

The route-order regression retained the public-site baseline of 94 owners and
352 routes after KAN-182 added `POST /api/auth/activity`. This branch still has
94 owners, with the activity endpoint registered by the existing auth owner.

The regression now records that single reviewed `(owner, method, path)` addition
and requires it to exist. The total remains an explicit baseline plus the
reviewed additions, giving 353 routes. Enquiry and Brief settings routes belong
to other branches and are not included here.

All existing overlap, reverse lookup, OpenAPI, endpoint, dependency, metadata,
HTTP matching, redirect and unsupported-method comparisons remain intact. No
application route or reference registration order changes. This follows the
reviewed KAN-169 inventory pattern without importing its enquiry owners.

Validation: the complete route-order file passed, six tests in 13.70 seconds,
using the worktree's private Python environment with shared database settings
cleared. The coordinator independently reviewed the exact addition and retained
contract assertions without findings. No full backend suite, live services or
external providers were used for this test-only reconciliation.
Ruff, formatting and `git diff --check` passed. The touched test file is 157 lines.
