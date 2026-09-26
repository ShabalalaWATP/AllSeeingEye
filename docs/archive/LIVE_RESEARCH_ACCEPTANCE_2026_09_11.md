# Live OpenAI and research acceptance, 11 September 2026

The operator supplied an OpenAI credential. Model discovery returned 136 models,
including `gpt-5.6-luna`. The existing OpenAI Luna profile retains maximum
reasoning and initially a 16,000-token configured output budget. A normal application
connection test succeeded and the normal audited activation use case created the
global binding. No alternative model or lower reasoning effort was substituted.

The API key is encrypted in the local database. The missing local encryption key
was replaced in ignored `backend/.env` after preserving a SQLite recovery copy.
One existing administrator authenticator record was already unreadable because
its original encryption key was missing. Its ciphertext remains untouched in the
database and backup. That authenticator still needs original-key recovery or an
explicitly authorised MFA recovery. No MFA was disabled or bypassed.

The intended local database was at migration `0026`. Activation exposed the
missing personal-binding column. After a second SQLite backup, the existing
reviewed migrations advanced it to `0032`. SQLite quick-check returned `ok` and
foreign-key check returned zero violations. The local API was restarted. Health
and frontend login returned 200; unauthenticated photo geolocation returned 401.

## Provider compatibility

An actual Chat Completions request rejected `max` reasoning for this model.
Responses accepted the same model and effort with valid structured output. The
gateway now uses Responses only for explicit maximum reasoning at the exact
official OpenAI base URL. Existing compatible origins and other efforts preserve
their prior transport. This follows the documented
[Luna capabilities](https://developers.openai.com/api/docs/models/gpt-5.6-luna),
with the endpoint distinction established by actual requests.

The first full research attempt exposed two additional integration failures:
OpenAI rejected a missing required nullable field in the report schema, and
native web discovery exhausted its separate 6,000-token output allowance. The
failed report and first results were preserved. Subsequent checks must be recorded
as checks after these fixes, not as successful first attempts.

## Public photo examples

These checks use public photographs through production import, sanitisation,
vision, report, deletion and retrieval use cases. A separate local harness uses
the existing Mock Research User and rechecks its active identity/security version.
It does not exercise HTTP login, MFA or refresh-family authentication; those
boundaries have separate deterministic integration tests. No raw private user
image was used and no source-page identity or geographic hint was sent to vision.

- Positive: [National Park Service Statue of Liberty photograph via NIST](https://www.nist.gov/image/statueoflibertyonislandjpg).
  The 3,495 by 2,365 original exceeds the existing eight-megapixel limit and was
  rejected before any model call. The publisher's 960 by 650 version was then
  imported. Its first vision response identified the Statue of Liberty and the
  United States. The returned landmark point was approximately 11 metres from
  the reference point, inside its stated 150-metre uncertainty radius. It
  distinguished the monument from the unknown camera location. This one example
  is not an accuracy estimate or a calibrated radius.
- Negative: [National Weather Service low-cloud example](https://www.weather.gov/key/low_clouds),
  the first small photograph of clouds above a generic flat airfield. Its first
  response returned `unknown`, no candidates and no coordinates. It recognised
  that the foreground and distant structures were ambiguous and suggested checks.
- The original failed-schema photo report still preserved six frozen evidence
  items. Deleting original and derived working receipts left that evidence
  unchanged. The saved response contained no image payload or transient receipt
  identifiers. Its empty failed report body does not count as successful writing.

Image credits, source URLs, byte hashes, first model responses and local report
artefacts are retained in ignored `output/live-research`. Image files, credentials
and private database backups are not part of the source commit.

## Multi-country research

The first actual Quick request covered Ukraine and Russia over a fixed seven-day
UTC interval, with Google News, BBC, DW and Guardian headline collection plus
optional native web discovery. The application retained 13 evidence items, all
graded F6, from two represented publisher organisations. Original title/summary
country matches carried exact spans and an unverified-geography notice. No
coordinates or incident countries were invented. The saved report honestly has
failed status because its body could not pass the provider's schema contract.

## Checks after the schema and web-budget fixes

The photo report was regenerated from its frozen evidence after the working
uploads had been deleted. The corrected schema was accepted, but both ordinary
120-second model requests timed out. Version 2 is retained with failed status;
no report text or model quality claim is inferred from that failure.

The next photo report used a 300-second request deadline, retaining the existing
600-second overall limit and two-attempt cap. Version 3 again failed, this time
with the provider reporting an incomplete response. The saved gateway error does
not include its incomplete reason or failed-call usage, so it does not prove
exhaustion of the configured 16,000 tokens. Report token totals exclude failed
ordinary gateway replies and are not complete billing totals. No partial output
was accepted as a successful report.

The second multi-country run completed native response generation but failed the
strict search-completion check. A separate bounded diagnostic retained its raw
public response: three completed searches and a fourth unfinished search item
were returned despite the requested three-call limit. The application rejected
that context rather than treating unfinished tool work as verified completion.
The diagnostic's final console summary initially failed on the Windows default
text encoding; the saved UTF-8 response was then inspected without another call.

The native request now permits the model to finish an answer after searching,
with explicit search-budget instructions. Successful acceptance still requires
actual completed search calls and attributable citations within the hard limits.

The third multi-country run passed those transport checks: two searches, eight
native citations and 64.97 seconds. Its context retained both countries and stated
coverage gaps. It stayed separate from the 13 frozen F6 evidence items. The report
body still failed with an incomplete provider response; automatic planning and
search revision had also fallen back to the original operator choices.

This accepted web context was generated before the subsequent claimant/date
instruction changes. An independent three-claim review again found the 2022 Mercy
Corps statement wrongly presented as current. DTEK's 1,446-family count was
supported, but a 4 September page describing work done "yesterday" implies
3 September, before the requested interval. Direct retrieval of that page was
unavailable during the review, so this date inference is qualified. The AP grid
targeting claim was supported by an [AP-authored republication dated 10 September](https://www.wcax.com/2026/09/10/zelenskyy-visits-canada-seek-further-military-support-ukraine/).
Its 2023 file-photograph caption was not the article publication date. Direct
canonical AP retrieval was unavailable. Passing transport checks does not settle
these factual and temporal questions.

## Confirmed reasoning-token exhaustion

The next photo run retained only allowlisted response metadata through a local
diagnostic wrapper, passing each response to the unchanged production parser.
Both draft attempts returned `incomplete`, with reason `max_output_tokens`:
exactly 16,000 output tokens, all attributed to reasoning, and no answer message.
Version 4 is retained as failed. This confirms the allowance problem for those
attempts, without retrospectively asserting the cause of every previous timeout.

The normal create, test and audited activation use cases replaced the global
connection with **OpenAI Luna Max**, retaining the same supplied credential,
model and maximum effort, with a 32,000-token allowance inside the existing app
limit. Its connection test passed and the global binding advanced to revision 2.
No team/person override was introduced. Earlier frozen report routing remains
unchanged. The native web stage retains its separate 16,000-token hard ceiling.

This allowance is consistent with OpenAI's recommendation to initially reserve
at least 25,000 tokens for reasoning plus output, although it cannot guarantee
completion. Reasoning can consume the entire allowance without a visible answer.
See [OpenAI's reasoning allowance guidance](https://developers.openai.com/api/docs/guides/reasoning#allocating-space-for-reasoning).
No model downgrade or further deadline increase was made.

## Final Max checks and remaining acceptance

With 32,000 tokens, the first photo draft again exhausted its entire allowance on
reasoning. Its second attempt returned a body using 29,333 output tokens, including
25,849 reasoning tokens. Version 5 was saved as `needs_review`. This is **not a
validated report**: 11 descriptive strings were removed from judgement citation
arrays, leaving all three judgements without supporting references. The saved
findings contain 14 errors and two confidence warnings. The independent review
confirmed that the narrative preserved the provisional landmark, unknown camera
position and unresolved authenticity/capture date. All 43 references in reporting,
assessment and alternatives resolved; the judgement references still require repair.

The parallel multi-country run also exhausted 32,000 reasoning tokens on its first
draft. Its second attempt was cancelled by the 600-second harness deadline and
produced no final acceptance JSON. No third attempt or automatic model downgrade
was made. Metadata and previous saved versions remain available locally.

The operator was asked whether to test High reasoning and apply it after successful
report checks, or retain Max and the current limits. Until an answer arrives,
the tested Max connection remains selected. A larger allowance alone has not
established reliable full-report generation, and no broad quality claim is made.

The follow-up efficiency repair distinguishes confirmed native token exhaustion
from transient failures. It stops an identical-budget retry, discards partial
output and adds validated known failed-call token counts once through the existing
usage writer. Unknown counts remain unknown. Transient failures and schema repairs
retain their existing retry policy. This change was verified deterministically;
the live runs above preceded it and retain their actual two-attempt history.

The citation repair constrains new report references to exact supplied-style IDs
such as `E1`, with matching strict input validation. It does not extract prefixes
from descriptive strings, relax evidence membership checks or rewrite historical
reports. Its live effectiveness remains to be measured after the reasoning choice.

## Final software verification

The root report/provider selection ran 520 tests across 38 files: 519 passed and
one already-collected fixture used a descriptive invented citation while expecting
the old membership-error wording. The fixture now uses syntactically valid `E999`
to preserve that membership test. All 117 tests in the affected report-integrity,
direction-coverage and new evidence-ID modules passed on the corrected checkout.
The complete selection was not rerun. The separate retry/accounting selection
passed 162 tests; these counts overlap and must not be added as unique tests.

The new-connection preset passed 35 frontend tests and 33 evaluation tests.
Independent security review passed 72 focused checks with no findings. Backend
Ruff/format, mypy across 786 source files, both import contracts, scoped Bandit
and file-length checks passed. Frontend typing, changed-file lint and formatting
passed. The existing untouched 380-line MapLibre target-length warning remains.
No new full-suite coverage measurement is claimed.

The final API restart returned health 200, frontend login 200 and unauthenticated
photo analysis 401. Read-only configuration verification confirmed the enabled,
tested global Luna Max profile with a 32,000-token allowance and the exact official
base URL. Scanning non-ignored source against configured secrets and the decrypted
stored OpenAI key found no plaintext matches. All live artefacts, images, credentials
and recovery databases remain ignored local files. No remote push or production
deployment occurred.

## Independent factual spot-check

A reviewer checked three substantive claims in the rejected native-web diagnostic.
The [AP article](https://apnews.com/article/6670c99dcc9ed149a2bd9c0deac455cf)
attributes the Mykolaiv facilities claim to Russia's Defence Ministry, not
Ukrainian authorities as the generated text stated. It describes attacks overnight
into 9 September; the generated 9–10 September range was not established.

A purported current Mercy Corps statement about three nuclear shutdowns repeats
[the joint statement published by NRC on 25 November 2022](https://www.nrc.no/news/2022/november/humanitarian-organisations-condemn-attacks-on-civilian-infrastructure-ukraine).
A current date on a redirected publisher page did not make that event current.
The preparedness delays and UAH 67.6 billion, including 43.7 billion for protection,
were supported by the [9 September government statement](https://www.kmu.gov.ua/en/news/serhii-koretskyi-doruchyv-pryshvydshyty-vykonannia-planiv-stiikosti-rehioniv-do-pochatku-opaliuvalnoho-sezonu).
That source does not establish realised nationwide outages.

The fresh-web instructions now distinguish claimant, event date and republication
or update date, and require historical/uncertain claims to be labelled accordingly.
This is risk reduction, not factual verification or a measured accuracy gain.
The diagnostic remains rejected; it was never admitted as report evidence.
