# ADR 0023: Software licence and organisational deployment offer

Status: proposed, awaiting Alex's decisions and approval. Prepared 9 October 2026
for [KAN-164](https://alex-orr.atlassian.net/browse/KAN-164). This document does
not grant rights, change the repository's visibility or approve a public launch.

## Current evidence

The repository is public and has no project-wide LICENSE file. Separate notices
for bundled fonts, reference data and test fixtures remain in force. Public source
visibility alone does not establish a general deployment or redistribution licence.
GitHub's terms permit viewing and forking public repositories; that is distinct
from an explicit software licence. See [GitHub's licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).

The software supports self-hosted research. `/enterprise` is an opt-in product
page controlled by `ASE_PUBLIC_PRODUCT_PAGE_ENABLED`. Its existing deployment
copy is a capability description, not evidence of approved commercial terms,
response times, source permissions or a support agreement. The maintainer's
security-reporting address is not assumed to be a business/privacy contact.

## Decisions for Alex

| Decision | Concrete choices | Consequence |
| --- | --- | --- |
| Software rights | A: organisation-specific proprietary agreement; B: source-available ELv2; C: AGPL-3.0-only plus optional paid support | A requires an approved agreement before granting deployments. B permits broad use with its stated hosted-service and other restrictions. C grants open-source rights with copyleft obligations, including the applicable modified network-service source obligation. |
| Public source | Keep public or approve making private separately | Visibility is not a substitute for licensing; changing it cannot recall existing copies. |
| Offer | Approve the bounded draft below, or edit its included services | No response-time, maintenance, pricing or availability promise exists until agreed. |
| Trading party | Legal/trading name, company or sole trader, business contact address and contact email | Required before identifying a supplier or controller in public text. Do not publish a residential address by inference. |
| Markets | UK only initially, or specify additional countries | Assess actual service, targeting and processing before drawing legal conclusions. |
| Source rights | Source-by-source permission and attribution review under KAN-194, with KAN-195 deployment controls | The software licence never supplies licences to third-party source data, maps, media or model services. |

These are alternatives, not an automatic recommendation or licence selection.
ELv2's restrictions are defined by its [licence text](https://www.elastic.co/licensing/elastic-license/)
and [publisher FAQ](https://www.elastic.co/licensing/elastic-license/faq/).
AGPL's network-source requirements are explained in the
[GNU licensing FAQ](https://www.gnu.org/licenses/gpl-faq.en.html#UnreleasedModsAGPL).
Before adopting either, confirm authority to license contributions and compatibility
with distributed third-party components. A proprietary agreement needs its own
reviewed grant, restrictions, warranty and liability terms; none are drafted into
source code by this ADR.

## Draft offer for approval

Proposed public wording, not approved for publication:

> Discuss a self-hosted All Seeing Eye installation for your organisation. We can
> assess deployment requirements, help configure an approved AI provider and
> review source options against their terms. The scope of implementation,
> maintenance and support is agreed in writing before work begins.

Proposed inclusions: deployment planning for a supported Linux/Compose installation,
configuration guidance, account and team setup, agreed AI-provider connection setup,
source eligibility review, upgrade and backup guidance, and an agreed handover.

Proposed exclusions: hosting and model charges, third-party data licences, legal
clearance, guarantees of research accuracy or completeness, monitoring on a
customer's behalf, emergency support, uptime or response-time commitments, and
unlimited bespoke development. Any separately purchased service needs a written
scope. Do not advertise AWS Bedrock or another integration beyond capabilities
verified in the current release. No public price or unapproved estimator figure
forms part of this proposal.

The final contact line must identify the approved trading party and business
contact. Those facts remain outstanding; this draft deliberately provides no
invented name, address or email. KAN-165's privacy wording and the enquiry launch
remain dependent on that approval.

## Territorial and source review

Accepting an organisation based in the EU does not, by itself, establish every
obligation asserted in the historical ticket. EU GDPR territorial scope and any
Article 27 representative requirement depend on the actual activities, with
exceptions to assess. DSA applicability depends on the service's role and scope.
Record a case-specific determination before expanding the offer. References:
[ICO on receiving EEA information and representatives](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/international-transfers/receiving-personal-information-from-the-eea/)
and the [European Commission's DSA overview](https://digital-strategy.ec.europa.eu/en/policies/digital-services-act).
This is a decision record, not a legal determination.

Keep unverified and non-commercial source rights explicit. Source attribution,
redistribution and hosted-use conditions must follow the approved register. A
customer acknowledgement cannot override a prohibition or manufacture permission.

## Approval and completion

Record Alex's selected model, approved offer, trading details, market scope and
approval date here before changing status to accepted. Then add the selected
project licence through its reviewed PR, reconcile README/SECURITY/public copy,
and link the approved notice and source policies. A licence selection does not
authorise production deployment or repository visibility changes.

Approval record: pending. No licence or commercial offer has been adopted by this
change. KAN-164 remains open until the required decisions are supplied.
