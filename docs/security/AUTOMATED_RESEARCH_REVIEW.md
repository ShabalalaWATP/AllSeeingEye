# Automated research security review, 6 September 2026

The independent review found two medium issues in long-request session handling. Both were fixed and verified locally. No confirmed issue remains open in the reviewed boundaries. Coverage is focused and partial: 59 of 227 source-like changed paths received complete source review; the remaining paths are recorded separately. Tests executed without reading every test file do not count as complete source review.

## Findings repaired

| Finding | Evidence and affected boundary | Resolution |
| --- | --- | --- |
| Medium: report generation could save after its original session ended | Pause a scripted model response in the real local HTTP report pipeline, revoke its session family or expire its JWT, then resume. The original implementation returned 201 and inserted a report even though new requests with the token returned 401. `api/report_run.py:91`, both mutations in `api/routers/reports.py`. | Both routes preserve original claims. The shared callback checks fresh session state at the saving stage, after final account/team authorisation and before usage/report persistence. |
| Medium: private upload extraction could be retained after its original session ended | The upload worker reproduced logout, expiry and logout/new-login variants returning 201. The reviewer traced `application/research/inputs.py:96` and independently verified the repaired HTTP path. | An optional application callback revalidates the original HTTP session immediately before `store.put`; failed or cancelled checks release admission without retaining the extraction. |

The shared `api/session_guard.py` uses fresh committed account/family state and checks original JWT expiry again after awaited database reads and session close. It prevents requests already invalid at that boundary from retaining data. It does not promise to undo a commit racing logout after the final check.

## Checks actually performed by this reviewer

- Local source review of raw upload admission, private storage and previews, parser/process cleanup, media tools, private report reuse, outbound credential origin/SSRF controls, and text export boundaries.
- Two pre-fix report HTTP reproductions against disposable in-memory SQLite, using synthetic accounts and paused model responses.
- Four independent post-fix HTTP regressions: upload/report crossed with family revocation/original-token expiry. All returned 401 with no retained input or report. Expiry cases started ten seconds before expiry and advanced eleven seconds while work was paused.
- 140 focused tests passed: feed credentials, research transport, follow-ups, private report inputs, worker boundary and cleanup, media protocols/tools, and real app upload wiring. No coverage percentage was measured in this reviewer run.
- Static applicability triage of the image scan supplied by the orchestrator. This reviewer did not execute a new image scanner, whole-repository SAST/secret scanner, public target scan, or production DAST.

Private document/media focus excludes public research and contrary-search collection. Parent reports require current read access and exact owner/team scope; frozen evidence keeps its prior provenance and dates. Connector credentials are per request, bound to an exact HTTPS origin, with redirects and validator caching disabled. Text is escaped for Markdown/PDF and rendered through React text nodes; preview PNGs are generated from decoded pixels in the worker. These observations are control evidence, not an ASVS compliance claim.

## Residual limits and image triage

The updated media image's supplied Trivy JSON contains **233 HIGH/CRITICAL package matches: 7 critical and 226 high**, while its fix-available HIGH/CRITICAL result is zero. The latter is a filtered result, not a clean image. Package matches include repeated findings across binary packages, and full advisory applicability has not been established.

Selected call-path triage found useful counterevidence: the Tesseract issue requires a malicious `.traineddata` model, while this app loads the trusted installed English model; the HEVC issue concerns Vulkan hardware decoding, which this command does not enable. A PNG encoder advisory initially appeared relevant, but the scanned upstream FFmpeg 7.1.5 source lacks the cited EXIF serialisation routine. These checks narrow individual hypotheses; they do not resolve every distribution advisory or justify blanket suppression. Sources: [Tesseract advisory in Debian's tracker](https://security-tracker.debian.org/tracker/CVE-2026-73066), [HEVC advisory](https://security-tracker.debian.org/tracker/CVE-2026-64831), [FFmpeg hardware defaults](https://ffmpeg.org/ffmpeg-all.html#Advanced-Video-options), [PNG advisory](https://security-tracker.debian.org/tracker/CVE-2026-66040), [upstream 7.1.5 encoder source](https://raw.githubusercontent.com/FFmpeg/FFmpeg/n7.1.5/libavcodec/pngenc.c).

The worker is a **resource boundary, not a filesystem or network security sandbox**. Native decoders run as the API user. A decoder code-execution flaw could reach same-user files, process interfaces and network access; a read-only root, stripped environment and no-new-privileges do not isolate the writable app-data mount. Stronger protection requires a separate restricted decoder service or equivalent OS sandbox with per-job input/output only, no application secrets/data mount, no network, and aggregate process/memory limits. Windows job memory is aggregate; POSIX address-space limits are per process.

Import access expires after 15 minutes, with bounded lazy removal on later store access. This is not a guaranteed timed physical RAM wipe. Configured LLMs receive selected private content as part of analysis. No operator database or public deployment was used for this review.

## Final implementation checks

The orchestrator subsequently ran the full backend suite (1,428 passed, 96.47%
coverage), the full frontend suite (453 passed), and a separate 19-test PostgreSQL
run covering both SQLite skips and session guards. Semgrep completed 457 rules on
1,065 source targets with zero findings. Two XML import matches were annotation
types only and received narrow documented suppressions; parsing uses defusedxml.
Gitleaks scanned 5.33 MB of backend/frontend application source with no leaks.
Bandit and Python/frontend dependency audits passed. Both final container builds
passed the fix-available HIGH/CRITICAL gate; unfixed distribution risks above remain.
