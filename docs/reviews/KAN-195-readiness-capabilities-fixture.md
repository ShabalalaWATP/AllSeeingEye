# KAN-195 readiness capabilities fixture

[PR 188 backend shard 4](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38010413595/job/114090100210)
failed the research-readiness response assertion at `dc5e0565`. The fixture
expected the three original capability fields, while the reviewed commercial
source policy intentionally adds `commercial_use` and `source_licences`. The
failure reproduced locally: one failed test in 2.23 seconds.

The fixture now exercises both commercial and non-commercial settings with no
licence acknowledgements. It keeps exact top-level response equality and checks
the complete public map/camera source set. Every licence entry is restricted to
the six approved fields, with validated policy values, boolean flags, public
reference structure and effective availability. The EOX prohibition anchors the
commercial-mode refusal expectation.

The existing provider lifecycle remains: research is unavailable before a
connection, available after a tested assignment and unavailable after disabling
it. All three states now require the complete expected response. The private
provider label, model, endpoint, hostname, key, ciphertext, profile ID and
provider-name nondisclosure assertions are unchanged. No production code or
coverage thresholds change.

Validation:

- Readiness, commercial source API and public refusal-reason files: 21 passed
  in 10.73 seconds.
- The three remaining direct capability cases for source policy and configured
  or unconfigured map keys: 3 passed in 3.52 seconds.
- Ruff, formatting and `git diff --check` passed. The touched file is 211 lines.
- Independent source/security review found no actionable issue and confirmed
  the exact public shape and retained private-configuration checks.

Tests used the private worktree environment and SQLite with shared database
environment variables cleared. Requests stayed within local fixtures, with no
live providers. The full suite and coverage were not rerun for this fixture-only
repair.
