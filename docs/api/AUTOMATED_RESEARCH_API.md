# Automated research API

Status: implemented contracts as of 6 September 2026. Final full-suite, security
and configured-model acceptance remains pending. See the
[master plan](../MASTER_AUTOMATED_RESEARCH_PLAN.md) for recorded evidence.
All paths below require the existing bearer session and current user authority.

## Generate and continue

`POST /api/reports` returns `201` with `report` and frozen `version`. Research uses
the existing report generation service and personal/team access policy.

| Field | Contract |
| --- | --- |
| `template` | Existing report template, commonly `ask` |
| `question` | Required and non-blank for research; at most 1,000 characters |
| `research_mode` | `quick` or `detailed`; omitted retains existing report behaviour |
| `research_focus` | `general`, `company`, `domain`, `document` or `media` |
| `research_subject` | Optional explicit record subject, at most 300 characters; required where the selected capability needs an identifier |
| `research_languages` | One to eight language codes, default `en`; edition choice does not prove actual language coverage |
| `window_hours` | Optional 1 to 336-hour publication window; internal receipts freeze concrete UTC bounds |
| `country` | Optional two-letter scope for general research; rejected with non-general research focus |
| `team_id` | Explicit team scope or null for personal scope, subject to current access checks |
| `research_input_id` | An unexpired input belonging to the current user/security version |
| `parent_report_id` | Follow-up source report; requires authorised frozen evidence reuse and compatible scope |

Follow-ups are new report requests with `parent_report_id`, not a separate public
endpoint. They reuse authorised frozen evidence and record additional collection
separately. Reuse preserves captured source context rather than replacing it from
today's catalogue. `POST /api/reports/{report_id}/versions` regenerates an existing
report under current write authority. Historical versions retain their saved data.

Quick collection has a six-request, 45-second, 200-item budget; detailed collection
has 24 requests, 180 seconds and 800 items. Individual collection timeouts are 12
and 20 seconds respectively. Detailed challenge collection shares a further six
requests, 45 seconds and 200 items across judgements. Empty or exhausted searches
are gaps, not confirmation. These limits do not promise total model latency.

Document/media focus uses supplied private evidence and does not query public
providers with extracted terms. Schedules reject these focuses because transient
inputs expire. Company/domain snapshots have provider-specific temporal limits;
see [data sources](../02_DATA_SOURCES.md) and
[scheduled research](RESEARCH_SCHEDULES_API.md).

## Progress and cancellation

Optionally send a fresh UUID in the **request header** `X-Research-Run-ID` on report
creation or regeneration. It enables `GET /api/research/runs/{run_id}` while the
original POST remains open. It is not an idempotency key or a detached job request.
Reusing a reserved UUID is rejected.

The progress response contains `id`, `stage`, `started_at`, `updated_at`,
`expires_at` and nullable `report_id`. Stages are `planning`, `collecting`,
`drafting`, `challenging`, `validating`, `saving`, `completed`, `cancelled`, `failed`
and `timed_out`. Only completed progress carries a report ID. No raw question,
source material or model output is stored in progress records.

Records are process-local, expire after 30 minutes and are bound to the initiating
user and security version. Missing, expired or foreign records return not found.
Capacity is 32 records and at most two active tracked runs per user; completed
records can be evicted first. A restart loses progress, not saved reports. A
single API process is required for these stores and admission controls.

Generation has a 600-second request deadline. Disconnect or client cancellation
propagates into outstanding model/feed work. Timeout returns 504; a disconnected
request may have a 499 outcome that the departed client cannot receive. If saving
had started, a commit can win cancellation or its outcome can be uncertain after
a lost connection. **Check Reports before retrying.** Cancellation is not a
guarantee that no report was saved, and there is no separate cancellation endpoint.

## Private upload

`POST /api/research/inputs?filename=notes.txt` accepts raw bytes with
`Content-Type: application/octet-stream`, not multipart or an external URL.
The filename is at most 120 characters; the body is limited to 8 MiB and a
30-second upload deadline. Authentication/admission precedes body consumption.

The `201` response contains `id`, sanitised `filename`, `media_type`, `sha256`,
`imported_at`, `expires_at`, `event_count`, `extracted_characters`, a bounded text
`preview`, `limitations` and optional `previews`. Each media preview has `seconds`,
`sha256` and `png_base64`. There are at most three sanitised PNGs, 512 pixels per
dimension and 1 MiB combined decoded bytes. Preview bytes are upload-response
material, not persisted evidence or receipt JSON.

Supported document extraction includes TXT, CSV, JSON, PDF and DOCX with explicit
page/row/line/JSON-pointer/paragraph references. Limits include 50 PDF pages, 200
units, 1,800 characters per unit and 200,000 total extracted characters. Images
and videos add bounded metadata, English OCR and sparse frame references, with
runtime/format limitations exposed rather than invented outputs. Extraction does
not prove authenticity, origin, recording date, location or claim correctness.

The input expires logically after 15 minutes. Physical removal is lazy on later
store access; memory caps still apply. Administrators do not acquire access to
another user's transient input. Original uploads are transient; selected evidence
and bounded input metadata are frozen into the report without the transient input
ID. Subsequent work uses authorised saved evidence or requires a fresh upload.
Disconnect cancellation waits for worker termination and temporary-file cleanup.

The worker uses fixed arguments, a scrubbed environment, deadlines, a 512 MiB
resource boundary and child termination. Linux applies 512 MiB per process, not
across the whole worker tree. It is not a filesystem/network security
sandbox: a native parser compromise could retain the service user's file access.

## Saved disclosures and catalogue

Report versions expose collection receipts, citation checks, research context and
challenge records alongside selected evidence. Context distinguishes publication,
capture and observation times, keeps identity matches as candidates and labels
declared source chains. Model challenge agreement is not independent corroboration;
lexical citation checks do not prove entailment. Markdown, PDF and DOCX use saved
disclosures rather than recalculating historical methods.

`GET /api/sources` combines live connectors with supported research and private
import capabilities, including optional providers without keys. It returns stable
IDs/names, category/language, organisation context and source ratings, never
configuration URLs, API keys or provider errors. Research profiles are F/unassessed;
the static catalogue does not establish operational availability.

Receipt statuses distinguish `completed`, `empty`, `unavailable`, `unsupported`,
`failed`, `timed_out` and `budget_exhausted`. No result is not evidence of absence.
Current-session revalidation at long-running boundaries has focused regression
evidence: logout/expiry during paused upload or generation returns 401 without
retaining the input/report. Combined software checks pass; actual model quality
remains unverified. See the implementation plan and security review for evidence
and residual limitations.
