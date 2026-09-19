# Deployed source health, 19 September 2026

Read-only inspection of the signed-in administration overview and source registry
at `allseeingeyeosint.com` found a misleading count alongside real upstream issues.
No production configuration, credentials, source activation or deployment was changed.

## Observed counts

The screenshot showed 418 registry entries: 264 healthy, 9 failing, 5 blocked
upstream and 140 waiting. A later source-registry snapshot showed 263 healthy,
15 degraded and 140 idle. These are separate snapshots; feed health changes as
polls complete.

All 140 idle rows explicitly identify themselves as on-demand sources. There were
zero idle scheduled rows. The registry therefore contained 278 scheduled feeds,
of which 263 (94.6 percent) were healthy at inspection. On-demand registration is
not proof of successful research collection or satisfied credentials. Some entries
represent the research mode of a publisher also represented by a scheduled feed.

The admin API initialises default idle health for research-only entries. The UI
previously counted these as waiting for a scheduled poll, included them in the
live-feed denominator, and showed an irrelevant polling interval. Its existing
`test_available=false` flag distinguishes these entries from scheduled connectors.

## Actual degraded feeds

| Group | Sources | Observed condition |
| --- | --- | --- |
| Publisher HTTP refusals | Arab News, CISA KEV, The Indian Express, The Times of Israel | HTTP 403, no successful poll |
| Publisher HTTP refusal | Bangkok Post | HTTP 451, no successful poll |
| Existing upstream blocks | Australia ACSC, US CISA advisory RSS | Automated feed access unavailable |
| Application approval | ReliefWeb API | Configured application name rejected with HTTP 403 |
| Telegram public previews | Izvestia, RIA Novosti | No recognised public channel history |
| Aircraft-provider throttling | LADD, military, PIA, watched areas, worldwide sweep | HTTP 429; area collectors still returned partial results |

The overview also reported no global AI connection, no personal/team overrides
and no saved profiles. Research/report generation requires a configured model;
that is separate from feed collection.

## Local corrections

- Separate research-only entries from scheduled health in the overview and registry.
  An automatically paused failing circuit must not be labelled an operator switch-off.
- Add a bounded fallback on CISA KEV HTTP 403 to the
  [CISA-maintained catalogue mirror](https://github.com/cisagov/kev-data).
  CISA describes this as its own distribution, normally synchronised within minutes.
  Both requests use the existing guarded HTTP client. Other errors, including rate
  limits, retain their normal handling. Invalid mirror data remains a failure.
- Address shared aircraft-provider throttling with host-wide cooldown and stop
  regional batches on rate limits while preserving successful results.

The official mirror was fetched once locally through the app's HTTP client:
catalogue version `2026.09.18`, 1,716 records. This does not establish reachability
from the deployed server. No browser impersonation or access-control bypass was used.

## Verification

- CISA/connector regression slice: 62 tests passed; KEV connector coverage 94.87 percent.
- HTTP/ADS-B regression slice: 90 tests passed; scoped coverage 90.60 percent.
  Host pacing coverage was 100 percent and regional/squawk collection 98 percent.
- Frontend administration slice: 30 tests across four suites passed. No frontend
  coverage measurement was made for this focused run.
- Scoped Ruff, mypy, ESLint, Prettier and frontend type checks passed. Frontend
  production build passed with the existing large-chunk warning.
- Architecture import contracts, file-length gate and diff whitespace checks passed.
  The file-length check reports existing warnings outside the changed files.
- Independent static review found no actionable correctness/security issues in
  the changed paths. DNS pinning, credential sanitisation, response bounds and
  conditional-validator staging remain in place. This was not a repository-wide
  security scan or a full application test run.

## Remaining actions

- Deploy and verify these corrections through the normal production approval flow.
- Verify CISA mirror access and aircraft rate-limit recovery from the server.
- Obtain ReliefWeb application-name approval through its operator process.
- Review publisher-supported feeds and public Telegram previews for the remaining
  unavailable sources. Do not count blocked sources as healthy or guess content.
- Configure and test an AI connection before evaluating on-demand research.
