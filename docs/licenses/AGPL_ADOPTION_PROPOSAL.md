# AGPL proposal and adoption prerequisites

Prepared 11 October 2026 for KAN-164. Alex selected open source under AGPL-3.0
with optional paid support, then chose to retain the existing eye and prepare a
permission request. The existing ADR candidate is **AGPL-3.0-only**. This is a
proposal for review, not a licence grant, permission receipt or public launch.

## Scope and compatibility

The eventual grant would cover project-owned software whose rights the
maintainer can license. Preserve separately licensed components, reference
material, fixtures, fonts and provider data. Source visibility, a Git author
identity or an AI co-author trailer does not independently prove licensing
authority. Confirm authority over the project-owned contributions before adoption.

The copied React Bits Evil Eye has custom MIT + Commons Clause wording, recorded
in [the frontend notice](../../frontend/THIRD_PARTY_NOTICES.md). The notice's
licence text matches the [immutable upstream licence](https://github.com/DavidHDev/react-bits/blob/ecdd797468fc87f7b463157627d1174b0c36fdf5/LICENSE.md),
blob `6425315416e94469f28d0223a09f7285b2f785ab`. Its application-use permission
is accompanied by component sale, sublicensing and redistribution restrictions.
It must not be described as ordinary MIT.

The affected scope includes `EvilEyeSurface.tsx`, extracted shader/rendering/noise,
the wrappers and worker/fallback adaptations that use it, and captured PNG/WebP
eye artwork under `frontend/public/brand/`. Refactoring the renderer does not
remove the original rights. The local initial import is `6133c427`; the recorded
registry URL and retrieval date are not an immutable upstream component commit.

[AGPL sections 5, 10 and 12](https://spdx.org/licenses/AGPL-3.0-only.html)
require compatible terms for the combined work. The retained component's
restrictions prevent treating the complete existing frontend as cleared for an
unqualified AGPL grant. A root licence or a third-party carve-out notice alone
cannot supply the missing rights.

Alex chose to keep the eye. The [permission request](REACT_BITS_PERMISSION_REQUEST.md)
asks for a suitable additional grant, covering source, adaptations, captured
artwork and downstream commercial redistribution. It is prepared but not sent.
A reply must be checked against that exact scope before adoption; do not infer
permission from silence, a payment offer or a general statement about app use.

## Other retained notices

| Material | Existing record to preserve |
| --- | --- |
| Copied frontend component and eye captures | `frontend/THIRD_PARTY_NOTICES.md` |
| Bundled report fonts | `backend/src/ase/adapters/reports/fonts/LICENSE`, `OFL-NotoCJK.txt` and `OFL-NotoArabic.txt` in the same directory |
| MITRE cyber reference material | `backend/src/ase/adapters/cyber_reference/LICENSE.txt` |
| Camera catalogue provenance | `backend/src/ase/resources/cameras/NOTICE.md` |
| OASIS test fixtures | `backend/tests/fixtures/stix21/LICENSE` |
| NTIA reference implementation | `docs/licenses/NTIA_LFMF_LICENSE.md` |
| Source/provider permissions | `docs/SOURCE_LICENCES.md` and the source register |

This is a focused provenance inventory, not a complete dependency-licence
clearance. Installed package notices must also be retained when distributing
their code. The web image currently copies `dist`, so keeping a notice only at
the frontend source root is insufficient as a delivery plan.

## Prepared adoption changes

Once rights and wording are approved, the reviewed implementation should:

1. Add the unmodified AGPL version 3 text as the root `LICENSE`, with an explicit
   AGPL-3.0-only project notice and accurate exclusions for separate material.
2. Reconcile README, SECURITY and package metadata. Retain frontend
   `private: true`; adopting a licence does not request registry publication.
3. Deliver required third-party notices and the licence with source/built
   distributions, including frontend output and relevant container images.
4. Expose an accessible licence and corresponding-source route/link. It must
   identify the actual deployed revision and provide that revision's source and
   required build/install material. Linking only to moving `main` is insufficient
   evidence for a modified deployed version.
5. Verify the source/notice delivery in builds and images, preserving auth,
   privacy, source-permission and publication gates.
6. Record the actual adoption approval, then obtain the separate merge/release
   approval. Do not insert approval fields merely to make checks pass.

## Optional paid support wording

Draft, not yet approved for publication:

> The All Seeing Eye is planned to be available under AGPL-3.0-only. Optional
> paid assistance can cover deployment planning, account and team setup,
> supported AI-provider configuration, source eligibility review, upgrade and
> backup guidance, and an agreed handover. Scope and charges are agreed in
> writing before work begins. Buying support does not replace the software
> licence or grant rights to third-party data or services.

After actual adoption, replace the first sentence with an accurate current
licensing statement. Hosting/model charges, third-party licences, legal
clearance, guaranteed research accuracy, emergency support and uptime/response
commitments are excluded unless separately agreed. AGPL permits paid support;
this draft does not create a supplier contract or promise an SLA.

The trading party, public address/contact, markets and installation-specific
providers remain undecided. KAN-165 also needs actual processing/retention
decisions and approval of the rendered notices. No placeholder facts or approval
hash are supplied by this proposal.
