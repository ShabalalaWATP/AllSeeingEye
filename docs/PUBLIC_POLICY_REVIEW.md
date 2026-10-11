# KAN-165 operator review pack

Prepared 11 October 2026. This is a review aid for the existing public pages,
not an approved notice or a record of the installation's actual providers.
Alex confirmed on 11 October 2026 that this notice covers the current personal
installation, with Alex Orr as the public operator and `alexorr@yahoo.co.uk` as
the privacy-enquiry and complaints contact. Provider and processing decisions
remain unresolved. Keep unconfirmed content fields and the approval record unset
until the actual facts and wording are confirmed.

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
  2026. The complaints procedure and accessibility contact remain unconfirmed.
- Application behaviour and operator retention policy are separate. The existing
  notice describes limited deletion, shared-team records, exports, backups and
  provider copies without promising complete account erasure.

## Confirmed scope: current personal installation

The draft applies to Alex's current personal installation, with the operator and
privacy/complaints contact confirmed above. Confirm its users, providers and
processing. The scope choice does not establish that only Alex has access or that
optional features are disabled. Record those facts separately. Other installations
need their own notice.
No decision about a future commercial service or paid-support offer is inferred.

## Facts to supply, without credentials

The fields below are in
[`privacy.json`](../frontend/src/features/public-policy/privacy.json).
Explanations such as "no email delivery is enabled" are useful only when verified
for the actual installation. Example environment values and supported adapters
are not evidence that a provider is used.

| Fields | Information needed for the wording |
| --- | --- |
| `jurisdiction` | Operator location, intended user countries, and any applicable representative or DPO details. |
| `hosting`, `emailProvider`, `aiProviders`, `otherRecipients` | Actual service/provider names, processing locations, information sent to each, and relevant recipients such as push services, external media and research providers. |
| `internationalTransfers` | Which information leaves the relevant jurisdiction, the assessed transfer arrangement, and how to obtain details of safeguards where needed. |
| `complaintsProcedure` | The contact is confirmed above. Confirm how complaints are handled, including the actual acknowledgement, investigation and response process. |
| `retentionCriteria` | Periods or criteria for accounts/requests, saved work, audit/usage records, enquiries, email copies, exports and backups; who performs deletion and reviews exceptions. |
| `publicSourceAssessment` | Actual source categories, personal-data categories and purposes; sensitive-data handling, how affected people are informed, and any assessed exceptions. |
| `storageAssessment` | Assessment of the declared cookies, preference storage, optional push and external media, including how choices can be withdrawn. |
| `automatedDecisions` | Actual use of AI outputs or profiling, any decisions affecting people, human review and applicable safeguards. |

## Processing decisions to review

Each of the five purpose rows requires its own `lawfulBasis`. A browser permission
prompt, publicly available source, paid-support plan or passing test does not
select that basis. Record the chosen basis and supporting assessment, including
the interests pursued if legitimate interests is chosen. KAN-185 and KAN-187
cover the related impact/interests assessments and processing/retention records.

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

[`service.json`](../frontend/src/features/public-policy/service.json) also needs
`terms`, `businessDisclosure` and `accessibilityContact`. These are shared release
prerequisites for the public routes; the existing gate requires all three.
KAN-164/188 cover offer/terms/business decisions and KAN-193 covers accessibility.
Do not treat the React Bits permission request as a grant or enter hypothetical
business details merely to pass this gate.

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
