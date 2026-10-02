# Request correlation and board privacy test compatibility

KAN-41, PR 90, parent `6eeca4cf41134fea9070b22ab589f3ae44c7da99`.
The coordinator reported the same board-subject test failure in the SQLite and
PostgreSQL jobs of [CI run 36924455345](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36924455345).

The targeted test reproduced locally: the inaccessible report and missing
report both returned HTTP 404, `not_found` and the same safe message. Their
new per-request correlation IDs correctly differed, so comparing entire error
envelopes byte-for-byte was no longer the privacy contract.

The test now requires both 404 responses, validates each generated ID as
32 lowercase hexadecimal characters, requires it to match that response's
`X-Request-ID` header, and requires the two IDs to differ. After removing only
that independently validated field, it compares both complete bodies to the
same explicit code/message envelope. Additional fields, object identifiers or
different error messages still fail. All existing authorisation, thread-count,
cache-control, personal-report and archived-team assertions remain unchanged.

Validation: the original targeted case failed once; the repaired entire
`test_team_board_subjects.py` module passed all seven cases. Scoped Ruff lint,
formatting and whitespace checks pass after applying the formatter's required
layout. Tests used the worktree's private Python environment and in-memory
SQLite, with inherited ASE database/race/PostgreSQL variables removed.
No production source changed. PostgreSQL and full-suite verification remain
with fresh CI; no container, shared database, push or deployment was used here.
