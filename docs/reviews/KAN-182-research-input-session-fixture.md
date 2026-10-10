# KAN-182 research input session fixture repair

Checked on 10 October 2026 against KAN-169 base `b4faee1d`.

## Failure and repair

GitHub Actions run `38008132990`, job `114081601589`, failed
`test_api_targets_and_conversion_receipt_without_parser_rerun` because the upload
application's refresh-token repository double lacked `activity()`. The declaration
route correctly performs a session fence check before releasing private input.
KAN-182 added the repository activity contract to that check.

The test double now returns the domain `SessionActivity` value with a fixed
180-minute deadline captured when the fixture application is created. Passive
checks do not extend that deadline, and the family becomes inactive at expiry.
The real session fence and private-input release callbacks remain in the test
path. No production code or authentication dependency was bypassed.

## Validation

The failing declaration test reproduced locally before the fixture change with
the same `AttributeError`. The existing declaration conversion test then passed,
including its assertion that conversion does not run the parser again.

The following combined focused run passed all 33 tests in 21.35 seconds:

```text
python -m pytest tests/test_input_declarations.py tests/test_research_input_api.py tests/test_research_input_sessions.py tests/test_router_order.py -q --no-cov
```

This includes the existing upload cancellation, size, admission and original
session release checks. The route-oracle repair in that run is a separate commit.
Tests used this worktree's private Python environment and disposable SQLite
fixtures. Shared test database, token-race, rotation and PostgreSQL URL variables
were removed from the test process environment.

Ruff lint, Ruff format verification and `git diff --check` passed. Coverage was not
measured for this test-only repair. No live feed, production service or external
write was used. This fixture repair can be propagated independently of enquiry
routes to other KAN-182 descendants.
