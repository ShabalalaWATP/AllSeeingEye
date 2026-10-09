# Public privacy, storage and attribution pages

KAN-165 adds `/privacy`, `/privacy/requests` and `/attributions` outside the
authenticated application. Storage is a section of `/privacy`. These pages contain
structured React text, local styles and links, with no provider media. Privacy reads
only the same-origin public `/api/site` retention setting without credentials;
failure is shown as unavailable, never as a confirmed default.

## Current status: draft, publication blocked

The controller identity and contacts, complaints process, jurisdictions, hosting,
email and AI processors, other recipients, transfer arrangements, lawful bases,
retention criteria, public-source assessment, storage assessment and automated
decision description remain unconfirmed. No approval has been entered into
`frontend/src/features/public-policy/approval.json`. Local previews and CI image
builds remain possible; they do not grant publication or legal approval.

The administrator contact for the separate operator-assisted request procedure
was approved under KAN-23 on 7 October 2026. It is reused from
[personal-data operations](PERSONAL_DATA_OPERATIONS.md). That decision does not
establish the controller's identity or approve the wider notice. The page retains
the unsupported account-wide export/erasure limits and preserves shared team work.

## Editing and approval

The typed entry is `frontend/src/features/public-policy/content.ts`. Edit
`privacy.json` for installation facts and wording, and `storage.json` for
application-owned storage. Null decisions remain visible placeholders. Renderers,
styles and generated credits live beside these inputs. Do not substitute an assumed
lawful basis, invented retention period or a provider's marketing claim.

1. Confirm the actual installation, providers, recipients, processing and retention
   decisions with the operator. Assess UK/EU applicability and any representatives.
2. Obtain review of the complete notice, complaints route and public-source handling.
   A checkbox or successful software test cannot determine legal compliance.
3. Run `pnpm check:policy`, the UI tests and normal frontend checks. Regenerate
   credits with `pnpm gen:attributions` after changing the source register.
4. Run `pnpm check:publication`. Its expected failure lists unresolved decisions and
   prints the content SHA256 without reading application secrets.
5. Only after actual approval, record the approver, calendar date and exact content
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
missing lawful bases and a stale or absent approval stop deployment.

This controller change requires an operator-reviewed manual installation of the
matching controller files. The repository does not install the host controller.
An old controller rejects the changed `deploy_vps.py` under its existing upgrade
rule; it must not be bypassed. Manual releases must honour the same approval
boundary. Ordinary Docker/SBOM builds remain available for review. No live controller
installation, deployment or legal approval occurred.

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

KAN-172 supplies deferred public bootstrap and noindex metadata for the three draft
routes. Its device motion key moves to `components/brand/localMotionPause.ts`; the
storage declaration remains `ase.brand-motion`. Integrate and test both changes
together before treating the whole-App no-private-request boundary as verified.

## Primary guidance checked

On 10 October 2026, implementation referred to the ICO's
[notice information](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/what-privacy-information-should-we-provide/),
[indirect collection](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/when-should-we-provide-privacy-information/)
and [storage guidance](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guidance-on-the-use-of-storage-and-access-technologies/).
The ICO's [June 2026 complaints update](https://ico.org.uk/about-the-ico/media-centre/news-and-blogs/2026/06/new-data-protection-complaints-law-now-in-force/)
also confirms the need to establish an actual complaints process. These references
inform the review questions; they do not approve this installation's wording.
