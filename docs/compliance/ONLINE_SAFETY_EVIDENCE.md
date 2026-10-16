# Online safety: source evidence

Reviewed main `e1f36dcb04c8dbdbe8945c756b0ac2747ae63ad3`, 16 October 2026.
These relative links describe that revision; recheck them after product changes.
No live account/complaint/content inspection was performed. Evidence does not
establish user numbers, locations, ages or absence of incidents.

| ID | Source | Fact and limitation |
| --- | --- | --- |
| S1 | [Board service](../../backend/src/ase/application/teams/board.py), [board access](../../backend/src/ase/application/teams/board_access.py) | Members create/read/reply; authors edit their content. Fresh account/team authority gates access. Closed groups can still exchange harmful content. |
| S2 | [Linked subjects](../../backend/src/ase/application/teams/board_subjects.py), [mentions](../../backend/src/ase/application/teams/board_mentions.py) | Posts can link accessible reports/areas/drawings and notify active roster members. Outside-team handles do not become recipients. |
| S3 | [Report access](../../backend/src/ase/application/reports/access.py), [team copies](../../backend/src/ase/application/reports/team_copies.py), [access policy](../../backend/src/ase/application/access.py) | Scoped report reading/sharing and private-input disclosure confirmation. Copy recipients may later retain exports independently. |
| S4 | [Claims](../../backend/src/ase/application/reports/claims.py), [claim revisions](../../backend/src/ase/domain/claim_revisions.py) | User annotations and review/withdrawal states preserve research history. They are not a misconduct complaint workflow. |
| S5 | [Map workspace](../../backend/src/ase/application/map_workspace.py), [map data](../../backend/src/ase/domain/map_workspace.py) | Team-scoped drawings can contain user names/notes/locations. No conclusion of safe subject tracking follows from scope checks. |
| S6 | [Directory profile](../../backend/src/ase/domain/directory_profile.py), [directory service](../../backend/src/ase/application/account/directory_profile.py) | Authenticated discovery of opted-in profiles, bios/roles and avatars. Discoverability defaults false; display names do not establish verified identity/age. |
| S7 | [Invitation sender](../../backend/src/ase/application/teams/invitation_sender.py), [invitation inbox](../../backend/src/ase/application/teams/invitations.py) | Notes/team/inviter names reach selected recipients; exact-handle invitations can reach non-discoverable accounts. Not an unrestricted chat system, but still a communication surface. |
| S8 | [Moderation](../../backend/src/ase/application/teams/board_moderation.py) | Author removal and manager/admin moderation with tombstone, audit reason and mention cleanup. `_load` uses `write=True`; archived teams reject even administrator removal. No user-visible appeal/case workflow established. |
| S9 | [Account request schema](../../backend/src/ase/api/schemas.py), [request UI](../../frontend/src/features/auth/RequestAccountPage.tsx), [administrator approval](../../backend/src/ase/api/routers/admin_requests.py) | Email/display name/optional reason and administrator admission. No age assurance, age declaration or date-of-birth field in this flow. |
| S10 | [Current service rules](../../frontend/src/features/public-policy/service.json), [terms rendering](../../frontend/src/features/public-policy/TermsPage.tsx), [privacy procedure](../../frontend/src/features/public-policy/privacy.json) | Permission-only lawful research rules, misuse mailbox, privacy complaints and prohibition on harmful uses. No 18+ statement in these current rules. Policy text is not evidence of enforcement or live publication. |
| S11 | [Account restriction route](../../backend/src/ase/api/routers/admin_users.py), [current session](../../backend/src/ase/application/auth/current_session.py) | Account deactivation and current-state session checks can restrict access. They do not remove content or recover already-exported copies. |
| S12 | [Research composition](../../backend/src/ase/container/research.py), [collection](../../backend/src/ase/application/research/collection.py), [news](../../backend/src/ase/adapters/research/news.py), [video search](../../backend/src/ase/adapters/research/youtube.py) | Planned queries can reach external news/video and selected providers. Optional configuration/source budgets determine actual use. |
| S13 | [Fresh web research](../../backend/src/ase/application/reports/fresh_web_research.py), [web gateway](../../backend/src/ase/adapters/llm/openai_web_search.py) | Optional external web search and consulted URLs; the gateway explicitly requests external web access. Not merely internal saved-report search. Legal provider/control boundary needs review. |
| S14 | [Saved-report search](../../backend/src/ase/application/reports/search.py), [search route](../../backend/src/ase/api/routers/report_search.py) | Ranks the caller's visible stored report vectors. Sending query text for embedding does not turn this particular corpus into multi-website search. |
| S15 | [Enquiry endpoint](../../backend/src/ase/api/routers/enquiries.py), [schema](../../backend/src/ase/api/schemas_enquiries.py) | Optional deployment/enterprise enquiry flow. It is not a designated illegal-content report or moderation-appeal process. |

## Reviewed primary legal/guidance sources

- [Act sections 3](https://www.legislation.gov.uk/ukpga/2023/50/section/3),
  [4](https://www.legislation.gov.uk/ukpga/2023/50/section/4),
  [229](https://www.legislation.gov.uk/ukpga/2023/50/section/229) and
  [Schedule 1](https://www.legislation.gov.uk/ukpga/2023/50/schedule/1?view=plain):
  functional, territorial, search and exemption tests. Official indexed text and
  direct Schedule 1 HTML were read; the browser parser rejected some XHTML endpoints.
- [Ofcom risk guidance/profile v2.0, 25 June 2026](https://www.ofcom.org.uk/siteassets/resources/documents/online-safety/information-for-industry/illegal-harms/updates/risk-assessment-guidance-and-risk-profiles.pdf):
  four-step assessment, functional factors and separate harms. Read the actual
  current document rather than treating the original 2025 deadlines as new deadlines.
- [Ofcom illegal-content duties, updated 25 June 2026](https://www.ofcom.org.uk/online-safety/illegal-and-harmful-content/illegal-content-duties-under-the-online-safety-act):
  assessment, measures, records and review. The updated material includes serious
  self-harm and cyberflashing; their assessment has not been omitted.
- [Ofcom children's access guidance page, updated 29 June 2026](https://www.ofcom.org.uk/online-safety/illegal-and-harmful-content/childrens-access-assessment-duties-under-the-online-safety-act):
  stage-one age assurance and stage-two actual/likely child audience.
- [Act section 37(4)-(5)](https://www.legislation.gov.uk/ukpga/2023/50/section/37)
  and [Ofcom access-assessment guidance, paragraphs 2.34-2.36](https://www.ofcom.org.uk/siteassets/resources/documents/consultations/category-1-10-weeks/statement-protecting-children-from-harms-online/main-document/childrens-access-assessments-guidance.pdf):
  deemed likely child access after a missed first-assessment deadline, and Ofcom
  determination. Actual scope and dates remain unverified for this installation.

The public record contains no real user lists, complaints, harmful examples,
credentials or host-access details. Operational evidence belongs in protected
operator records and must not be added to this public repository.
