# Public privacy, storage and attribution pages

KAN-165 adds `/privacy`, `/privacy/requests` and `/attributions` outside the
authenticated application. KAN-172 adds `/accessibility`, `/terms` and `/business`
to complete the public footer. KAN-188 adds `/acceptable-use` and restructures
`/terms`; KAN-193 rewrites `/accessibility` as a statement following the GOV.UK
sample structure. Storage is a section of `/privacy`. These pages contain
structured React text, local styles and links, with no provider media. Privacy reads
only the same-origin public `/api/site` retention setting without credentials;
failure is shown as unavailable, never as a confirmed default.

## Current status: wording finalised under delegated approval

Alex confirmed the current personal installation, the public operator name
Alex Orr and `alexorr@yahoo.co.uk` for privacy enquiries and complaints on
11 October 2026. Read-only checks verified Hetzner Cloud hosting in Helsinki,
Resend email delivery and OpenAI API connections (GPT-5.6 Luna globally and
GPT-5.6 Sol for user-specific use).

Alex subsequently instructed: "You provide those, you have my permission, finish
this ticket." This delegates completion and adoption of the remaining notice
wording and operating commitments to Codex. It is recorded as delegated approval,
not a claim that Alex personally reviewed an exact hash. The
[operator decision record](PUBLIC_POLICY_REVIEW.md) distinguishes verified facts,
adopted policy and the remaining operational compliance work.

On 14 October Alex confirmed Finnish operation, a recorded Hetzner DPA, and
standard OpenAI/Resend terms with no opt-ins or custom settings. KAN-187 updates
the notice to EU GDPR and Finnish law, Finland's Data Protection Ombudsman and
EU transfer terms. The prior notice delegation covers this factual correction;
the confirmation does not constitute an independent account or legal audit.
The notice states the verified host location, Resend's published US storage and
the standard OpenAI/Resend transfer terms, with links to
the safeguards and a contact route. It does not certify account-specific contracts,
transfer-risk assessments, regional processing or zero retention. The adopted
complaints, retention, research boundaries and personal-installation terms retain
all supported-action and external-copy limitations.

The exact-content manifest attributes finalisation to Alex's delegation. Its hash
must match the complete policy inputs. Approval of this notice does not close
KAN-185/187, clear high-risk processing, adopt the pending software licence or
authorise an unreviewed production migration. The controller upgrade and rollout
remain distinct release work.

The administrator contact for the operator-assisted request procedure was
approved under KAN-23 on 7 October 2026. The 11 October confirmation extends its
use to privacy enquiries and complaints, and the delegated finalisation adopts
its use for accessibility feedback. Account-wide export/erasure limits and shared
team ownership requirements remain explicit.

## KAN-188 and KAN-193 status: drafted, not approved

The 18 October 2026 terms, acceptable use and accessibility drafts change the hashed
content, so the 14 October approval no longer matches and every policy page shows
the draft notice. The following decisions are recorded as `{ "pending": ... }`
entries or null fields and fail both publication checks until Alex decides them:

- governing law and courts (KAN-188 proposes England and Wales; the privacy notice
  applies EU GDPR and Finnish law);
- any limitation of liability;
- further consequences of breaking the Acceptable Use Policy (notice, appeal, referral);
- the geographic business address, or a decision that none is published (KAN-164);
- the expected response time for accessibility reports;
- the accessibility enforcement and complaints route.

The 18+ eligibility and professional or research use come from the KAN-188 scope
and still need Alex's approval with the rest of the wording. The accessibility
statement says "partially compliant" because no complete audit has been done; its
limitations were checked against the code on 18 October 2026, and its next review
date is 18 April 2027. Legal review is recommended before approval.

## Editing and approval

Use the [operator review pack](PUBLIC_POLICY_REVIEW.md) to collect the actual
installation facts and processing decisions before completing the notice.

The typed entry is `frontend/src/features/public-policy/content.ts`. Edit
`privacy.json` for installation facts and wording, `service.json` for business
disclosures, the business address and the accessibility contact, and `storage.json`
for application-owned storage. `terms.json`, `acceptable-use.json` and
`accessibility.json` hold structured sections: each paragraph or list item is
published text or `{ "pending": "<decision>" }`, rendered as a visible "Decision
needed" block. Null decisions and pending entries remain visible placeholders.
Changing the terms `version` also requires `CURRENT_TERMS_VERSION` in
`backend/src/ase/domain/terms.py`, which asks signed-in accounts to accept again
(see `docs/api/AUTH_API.md`). A backend test pins a hash of `terms.json` and
`acceptable-use.json`, so changing either fails until the version is bumped and the
hash updated. The consent wording outside this folder is not hashed: review the
checkbox text in `RequestAccountPage.tsx`, the re-acceptance dialog in
`components/account/TermsAcceptanceDialog.tsx` and the footer in
`components/privacy/PolicyLinks.tsx` as part of every approval. The installation terms
grant no software licence or deployment offer. Renderers,
styles and generated credits live beside these inputs. Do not substitute an assumed
lawful basis, invented retention period or a provider's marketing claim.

1. Confirm the actual installation, providers, recipients, processing and retention
   decisions with the operator. Assess UK/EU applicability and any representatives.
2. Obtain review of the complete notice, complaints route and public-source handling.
   A checkbox or successful software test cannot determine legal compliance.
3. Run `pnpm check:policy`, the UI tests and normal frontend checks. Regenerate
   credits with `pnpm gen:attributions` after changing the source register.
4. Run `pnpm check:publication`. Incomplete or stale content fails with the
   unresolved decisions and content SHA256; a matching approved manifest passes.
   The check does not read application secrets.
5. Review the version label and complete rendered notice. Only after actual approval, including an explicit delegation to finalise
   the stated scope, record the approver, calendar date and exact content
   hash in `approval.json`. Do not invent an approval as a build fix.
6. Re-run the publication check and review the built pages. Changed policy text,
   renderers, styles or attribution content invalidate the approval.

The Vite virtual module exports only a boolean from that same validation and hash.
A stale manifest cannot remove the draft notice. Local preview file additions,
edits and deletions invalidate the module. Hashing sorts file names, normalises CRLF
and surrounding whitespace, and excludes tests and the approval manifest. A test
compares Node and Python hashes for actual content. Vitest merges the Vite plugin
configuration, so it receives the same approval result.

## Deployment gate and manual installation

`scripts/privacy_publication.py` is part of the protected, root-owned deployment
controller set. It parses the target Git revision's regular blobs without executing
candidate code. `deploy_vps.py` calls it before image inspection, builds, backup or
cutover, including check-only runs. Missing files, invalid dates, placeholders,
missing lawful bases, incomplete service details and a stale or absent approval
stop deployment. Both checks parse every required JSON input and reject explicit
unresolved wording, including "not decided", "not yet confirmed" and "not yet
approved", even if a matching hash is supplied. These checks catch known draft
markers; they do not establish that arbitrary prose is complete or accurate.
Both Node and Python checks require all three service fields
(`businessDisclosure`, `businessAddress`, `accessibilityContact`), the three
structured documents with dated `version`, `lastReviewed` and `nextReview` fields,
and no pending entry, even when an approval hash matches the incomplete content.
The shared footer reads the operator name, contact and business address from the
same hashed files through the `virtual:policy-footer` build module.

This controller change requires an operator-reviewed manual installation of the
matching controller files. The repository does not install the host controller.
An old controller rejects the changed `deploy_vps.py` under its existing upgrade
rule; it must not be bypassed. Manual releases must honour the same approval
boundary. Ordinary Docker/SBOM builds remain available for review. This continuation records notice approval only. No live controller installation
or production deployment is implied by that record.

## Source and storage maintenance

Generated credits join every `source_licences.json` catalogue identity to both its
primary policy and every `additional_policies` entry. This is a superset of enabled
sources, so no authenticated configuration is exposed. Unknown and restricted rights
remain unresolved. Credits do not grant commercial, hosted, AI, export or republication
permission. See [the source register](SOURCE_LICENCES.md) and its evidence limits.

The declaration check scans application-owned frontend local-storage access and
backend cookie setters/deleters. It recognises constant and per-account keys and
Zustand persistence; unresolved keys or new browser-storage mechanisms fail closed.
It also catches undeclared keys added to the generic adapter. Tests cover new names
without an `ase` prefix. This is not a scan of external providers or proof that browser
vendors set no additional storage. Review new wrappers and APIs with the inventory.

KAN-184's `ase.embed-consent.v1` contains explicit persistent provider choices; its
default choice stays in page memory. Withdrawal and storage-failure behaviour are
described in the notice. Direct map/stream requests are separately declared. A media
gate does not establish that a consent banner is unnecessary.

KAN-172 supplies deferred public bootstrap and noindex metadata for all six policy
routes. Its device motion key moves to `components/brand/localMotionPause.ts`; the
storage declaration remains `ase.brand-motion`. Integrate and test both changes
together before treating the whole-App no-private-request boundary as verified.

## Primary guidance checked

The 14 October country correction uses EU GDPR, Finland's Data Protection Act,
the EDPB authority directory and Traficom's device-storage guidance, linked in the
[decision record](PUBLIC_POLICY_REVIEW.md). The earlier UK references below are
historical preparation evidence, not the default Finnish legal test.

On 10 October 2026, implementation referred to the ICO's
[notice information](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/what-privacy-information-should-we-provide/),
[indirect collection](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/when-should-we-provide-privacy-information/)
and [storage guidance](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guidance-on-the-use-of-storage-and-access-technologies/).
The ICO's [June 2026 complaints update](https://ico.org.uk/about-the-ico/media-centre/news-and-blogs/2026/06/new-data-protection-complaints-law-now-in-force/)
also confirms the need to establish an actual complaints process. These references
inform the review questions; they do not approve this installation's wording.
