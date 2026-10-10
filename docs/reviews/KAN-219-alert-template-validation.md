# KAN-219: executable alert report choices

Initial regressions showed a country brief without a country was accepted with
HTTP 201, while the form offered question, conflict and hazard products without
their required inputs. These jobs could only fail after the alert had fired.

The manual report builder and alert-rule validation now share template prerequisite
checks. Country briefs need one country. Question products use a question from an
authorised collection plan. Conflict and hazard products are unavailable because
the rule has no fields for their tracker inputs. Plan validation also checks its
question and linked area, with the same exact-area restriction as the report builder.
Plan and area scope checks remain mandatory and use non-disclosing error messages.

The frontend uses the existing published requirement flags to offer compatible
choices and scoped area metadata to verify a linked plan's report eligibility.
Unavailable or exact-shape areas retain No report with a repair explanation.
Unsupported saved choices remain selected and visibly explain recovery.
Creation, editing and resuming validate prerequisites; an unchanged incompatible
selection can be retained while paused, so old rules can always stop running.
Changing a rule does not reset old failed jobs or trigger provider calls.

Independent review identified two recovery and choice gaps: the report country
limit initially still blocked pausing a legacy nine-country rule, and the form
initially offered reports for exact-shape plan areas. Regressions now cover both.
Pausing skips only the report count limit while retaining country-code validation;
resuming requires repair. Unknown plan or area metadata cannot establish report
eligibility, but No report preserves the selected plan link.

A further production trace regression found that attaching frozen alert evidence
discarded the builder's plan-derived question. The wrapper now retains that question
in the request and saved job scope alongside its exact alert origin.

No migration, public schema, dependency or deployment configuration changed. Private
dependencies were installed frozen and offline. Tests clear inherited database
environment variables and use isolated SQLite and a synthetic model gateway.

## Verification

Backend coverage includes create/update prerequisite rejection, legacy pause and
repair, missing plan inputs, and production of all eight supported products. The
plan-backed products assert the frozen question as well as completed publication.
Frontend checks cover changing country/plan availability and repairing retained
selections. Existing report failure/progress, rule scope, pause and report production
tests cover adjacent behaviour. Final gate results and review are recorded below.

- The backend focused group passed 52 tests. Targeted follow-up runs passed four
  recovery tests and five plan/geography tests, including three additional cases
  beyond the original group. All 55 distinct selected cases passed.
- Frontend checks passed 28 tests across seven files after the review fixes.
- Ruff, mypy (1,598 source files), all three import contracts, Bandit on changed
  Python, Prettier and `git diff --check` passed. Changed handwritten files remain
  below 350 lines.
- Independent review corrections were rechecked without further findings.
- Final frontend type checks, production build and ESLint on all six changed
  frontend files passed. The earlier repository-wide lint run overlapped the AOI
  edits and reported four type diagnostics against the replaced boolean helper
  signature. Its eight script tests passed; repository-wide ESLint was not rerun.
  The stable touched-file lint and complete TypeScript checks supersede those
  affected-file diagnostics; full CI remains the integration gate.
- Coverage was not measured; no full suite or live provider calls were run.
