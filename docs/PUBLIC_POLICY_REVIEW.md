# KAN-165 operator review pack

Prepared 11 October 2026. This is a review aid for the existing public pages,
not an approved notice. The provider facts below were checked against the running
installation.
Alex confirmed on 11 October 2026 that this notice covers the current personal
installation, with Alex Orr as the public operator and `alexorr@yahoo.co.uk` as
the privacy-enquiry and complaints contact. The host, email service and configured
AI connections have since been verified. Alex then authorised preparation of the
remaining assessments and wording. Proposed operating commitments and purpose
assessments now appear in the draft. Jurisdiction and international-transfer
safeguards remain unset while factual questions are answered; the approval record
also remains unset until the complete wording is reviewed.

## What is already established

- `/privacy`, `/privacy/requests` and `/attributions` are public routes. They use
  structured React text. The privacy page reads the public retention value from
  same-origin `/api/site` without credentials and identifies an unavailable value.
- [The storage inventory](../frontend/src/features/public-policy/storage.json)
  describes two application cookies and nine local-storage keys, including
  per-account patterns. Browser push and external media are separately explained.
- The source page contains generated catalogue credits, including additional
  policies. This is not an inventory of an installation's enabled sources.
- The contact remains approved for the existing
  [operator-assisted procedure](PERSONAL_DATA_OPERATIONS.md). Alex separately
  confirmed the operator name and wider privacy/complaints contact on 11 October
  2026. The subsequent draft proposes a complaints procedure and reuse of the
  same address for accessibility feedback under Alex's authority to prepare the
  remaining wording.
- Application behaviour and operator retention policy are separate. The existing
  notice describes limited deletion, shared-team records, exports, backups and
  provider copies without promising complete account erasure.

## Confirmed scope: current personal installation

The draft applies to Alex's current personal installation, with the operator and
privacy/complaints contact confirmed above. A later aggregate database check found
one account. This does not establish the operator's country, the precise purposes
of use or a domestic-purpose exemption. Those facts are being clarified. Other
installations need their own notice.
No decision about a future commercial service or paid-support offer is inferred.

## Verified installation providers, 11 October 2026

Read-only checks at approximately 20:03 UTC established these facts for the running
installation at `allseeingeyeosint.com`, whose checkout was `13efceef48efbc6d5f2895e60c55076db5d40e3f`:

| Notice field | Verified fact | Evidence |
| --- | --- | --- |
| `hosting` | Hetzner Cloud, Helsinki, Finland (EU). | The host's Hetzner metadata returned `eu-central` and `hel1-dc2`. Hetzner's [location documentation](https://docs.hetzner.com/cloud/general/locations/) identifies `hel1-dc2` as Helsinki. |
| `emailProvider` | Resend, using encrypted SMTP. | The running API settings identify `smtp.resend.com` and TLS. Earlier KAN-22 evidence records actual delivery, not just a configured default. |
| `aiProviders` | OpenAI API, GPT-5.6 Luna as the global connection and GPT-5.6 Sol for user-specific use. | A database transaction set to read-only selected provider/model/endpoint and scope types. Both enabled profiles use `api.openai.com`; bindings select `gpt-5.6-luna` globally and `gpt-5.6-sol` for a user. Aggregate usage records also establish prior calls. |

The inspection did not select credentials, encrypted keys, user identities,
prompts or research content, and made no model calls or production changes.
Only provider identity and necessary configuration facts are recorded here;
host access details remain private. These facts populate the draft without
approving its wording. Recheck them when routing or deployment changes.

The models are selected by the applicable scope; both do not receive every task.
See [AI connections and inputs](AI.md) for routing and submitted-material behaviour.
The configured OpenAI and Resend endpoints do not establish their processing
countries, contractual transfer arrangements, account-level retention or training
settings. Those matters remain part of the separate transfer/retention review.

Further allowlisted runtime checks found feeds, conflict screening, Internet
Archive capture and browser-push configuration enabled, and no installation-wide
alert webhook or enquiry-email recipient. The running release predates the new
enquiry settings and public policy controls. Do not describe prepared controls as
already deployed or missing old-release settings as verified false flags.
Log rotation is five 20 MB files per container, with no age guarantee. Current
cron entries invoke the scheduled-backup helper daily and for a weekly drill;
they do not specify off-site copying, heartbeat reporting or a keep override.
No restore test was performed in this assessment.

## Prepared assessments and proposed commitments

The detailed initial DPIA, legitimate interests assessment, processing/recipient
register and retention schedule are retained in a Git-ignored local review pack
for Alex, consistent with KAN-185's restricted-draft requirement. They have not
been uploaded to this public repository or Jira. This public summary records the
decisions that affect the notice:

- A private complaints route, acknowledgement within 30 days, investigation,
  updates and an outcome without undue delay; rights requests keep their separate
  applicable deadline and the route to the ICO remains available.
- A quarterly manual review of necessity, plus review when an account closes,
  research ends or a rights request arrives. This is a proposed operating duty,
  not an implemented deletion job. Unsupported account-wide erasure, audit,
  notification and external-copy handling remain explicit.
- Proposed legitimate interests for access administration, security and narrowly
  assessed ordinary public-event research. Optional delivery uses consent.
  Enquiry wording is conditional on separate enablement and review.
- No blanket permission for special-category or criminal-offence data, no blanket
  indirect-notice exemption and no claim that the site notice informs everyone.
  Unassessed sensitive, tracking and consequential uses retain high risks and are
  outside the proposed permitted scope.
- Personal-installation access rules and accessibility feedback wording. These
  grant no software licence or commercial offer and do not finish KAN-188's
  acceptance workflow or KAN-193's full accessibility assessment.

The risk assessment distinguishes existing code, controls prepared for release
and manual commitments. It identifies residual risks from inaccurate AI claims,
combining records, sensitive information, location exposure, external disclosure,
persistent copies and incomplete deletion. It does not certify all current
processing or authorise a new source or use.

## Remaining facts and assessments, without credentials

The fields below are in
[`privacy.json`](../frontend/src/features/public-policy/privacy.json).
Explanations such as "no email delivery is enabled" are useful only when verified
for the actual installation. Example environment values and supported adapters
are not evidence that a provider is used.

| Fields | Information needed for the wording |
| --- | --- |
| `jurisdiction` | Operator location, intended user countries, and any applicable representative or DPO details. |
| `hosting`, `emailProvider`, `aiProviders`, `otherRecipients` | Provider identities and the hosting location are verified above. Complete the processing-location and recipient assessment for email, AI, push services, external media and research providers. |
| `internationalTransfers` | Which information leaves the relevant jurisdiction, the assessed transfer arrangement, and how to obtain details of safeguards where needed. |
| `complaintsProcedure` | Proposed procedure is filled. Review the operator's practical handling commitments in the complete wording. |
| `retentionCriteria` | Proposed manual criteria are filled. Unsupported deletion and external copies remain explicit; no unimplemented fixed erasure deadline is promised. |
| `publicSourceAssessment` | Proposed boundaries are filled. Complete source/purpose-specific sensitive-data and indirect-notice decisions before allowing those uses. |
| `storageAssessment` | Technical purposes and withdrawal are described. Do not infer a blanket PECR exception or a complete third-party tracking audit. |
| `automatedDecisions` | Proposed use restrictions are filled; confirm the actual use context and review changes before consequential or intrusive uses. |

## Processing decisions to review

Each of the five purpose rows now has proposed `lawfulBasis` wording supported by
the initial assessment. A browser permission prompt, public source or passing
test does not prove that every use meets the basis. In particular, the research
row requires a purpose-specific necessity and balancing decision and any additional
sensitive-data condition. KAN-185 and KAN-187 retain their review and factual
acceptance requirements; this continuation does not mark them complete.

| Purpose | Review question |
| --- | --- |
| Accounts and access requests | Why is each requested item necessary, and what happens if the person does not provide it? |
| Authentication and security | What security processing is necessary, who accesses its records, and how long are they needed? |
| Enterprise enquiries | Is this feature used by this installation, what response is requested, and where are submissions copied? |
| Research and public-source material | Which research uses are permitted, what personal information is used, and what reaches AI/research providers? |
| Notifications and web push | Which notification types are used, what choice is offered, and how are browser permission and server device records removed? |

The separate right-to-object section is draft wording for review. It makes the
route visible without asserting that every purpose uses legitimate interests.

## Related publication inputs

[`service.json`](../frontend/src/features/public-policy/service.json) contains
proposed personal-installation terms, operator disclosures and accessibility
contact wording. They do not invent a company, registration or address and offer
no paid service. KAN-164/188 cover the separate offer/licensing/acceptance scope
and KAN-193 covers full accessibility work. The React Bits request remains a
request, not a grant. The complete content still requires final review.

## Review and publication sequence

1. Complete the factual wording and purpose assessments for the chosen installation.
2. Review all six policy routes together, including requests, terms, business and
   accessibility. Replace the draft version label only when the wording is ready.
3. Run the checks in [the publication guide](PUBLIC_POLICY_PUBLICATION.md).
4. Present the complete rendered wording and content hash to Alex for actual
   approval. Only then record the approver, date and matching hash in `approval.json`.
5. Obtain the separate release approval and follow the documented controller
   upgrade procedure. A content approval does not authorise deployment.

The ICO's [privacy information guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/what-privacy-information-should-we-provide/)
and [timing guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/when-should-we-provide-privacy-information/)
were checked on 11 October 2026. The former is under review following legislation;
these references support the review questions, not an installation compliance claim.
