# Runtime integration, 30 September 2026

KAN-41, KAN-42 and KAN-43 are published in draft PR #90, on the architecture
batch in PR #89. The architecture/lifecycle integration passed 58 focused tests.

The first full CI run found two assertions affected by request logging. Login
failure tests now compare every account-neutral error field while separately
checking each response's correlation ID against its header. Secret transport
tests explicitly enable every transport logger, so preceding application
configuration cannot make secret-suppression assertions vacuously pass.

The repaired request logging, hardening, secret transport and login modules
pass 50 tests together in one process, preserving the order that exposed the
logging-level dependency. Ruff, formatting and whitespace checks pass.
The architecture test-container correction is inherited from PR #89.

Full CI, the populated Compose stop/start check and the reference-host restart
timing remain required. No production deployment was performed.
