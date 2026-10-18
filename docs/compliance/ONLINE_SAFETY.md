# Online safety scope and operating assessment

**16 October 2026, KAN-189. Owner: Alex Orr. Assessment record approved 18 October 2026.**

The reviewed application has user-to-user functionality. Alex confirmed approved
adult users, including UK users, on 16 October 2026. **For operational planning,
treat the user-to-user service as regulated under Part 3.** No exemption is
established. This conservative working scope does not prove a particular section 4
UK-link test, settle the search-component boundary or certify completed duties.
Alex approved this assessment record and conservative working scope on 18 October
2026, retaining the recorded legal/factual review in KAN-246. This approval is
separate from the earlier audience confirmation and does not resolve those facts.

Baseline: main `e1f36dcb04c8dbdbe8945c756b0ac2747ae63ad3`. The
[source evidence](ONLINE_SAFETY_EVIDENCE.md) identifies actual features and limits.
The [risk assessment](ONLINE_SAFETY_RISKS.md) includes a separate children-access
analysis. The operator's audience statement is recorded separately from code
evidence. User counts, independent age/location evidence, usage, complaints and
moderation outcomes have not been inspected. No private user records belong here.

## Service boundary and users

This assessment concerns Alex's current personal installation, operated from
Finland, not every deployment of the public source repository. The confirmed
permitted audience is approved adults, including UK users. Account approval and
current team membership restrict access. Within those boundaries, users can
post/reply on boards, annotate reports/maps, share saved reports, view opted-in
directory profiles/avatars and receive invitations/mentions. There are no verified
anonymous public report feeds in this reviewed surface. Restricted visibility
does not remove the ability to encounter another user's content.

Section 3 covers sharing functionality even where nobody has yet used it. This
means a currently small audience, or a claim that only the operator uses the app,
does not alone dispose of the functional definition. The code supports this
conclusion; actual deployment restrictions must be recorded separately.
[Online Safety Act section 3](https://www.legislation.gov.uk/ukpga/2023/50/section/3).

Research can query external news, video and other providers, with optional broader
web research. Saved-report semantic search is a distinct internal corpus. The
search definition excludes searching only one website/database but can encompass
multi-source search. Who controls any included search engine, including downstream
provider arrangements, needs legal confirmation before deciding whether this is
a combined service. Do not classify all search as internal merely because a saved
report is the final output. [Section 229](https://www.legislation.gov.uk/ukpga/2023/50/section/229).

## Exemptions considered

| Candidate | Application to the reviewed service |
| --- | --- |
| Email/SMS/one-to-one live voice only | Not the sole functionality: boards, reports, maps and directory content are independently shared. No reliance proposed. |
| Limited comments/reviews on provider content, and combinations of exempt functionality | Users originate posts, reports/annotations and profile content. This exceeds a service confined to comments on provider material. AI assistance does not automatically make all user-shared work provider content. |
| Internal business service, entire service or qualifying part | A closed group is insufficient alone. The service must satisfy the business/internal-purpose/provider/user conditions. No qualifying business relationship for all users or separately bounded exempt part is established. A non-profit concern can qualify in principle; calling this installation personal establishes neither inclusion nor exclusion. |
| Public-body or specified education/childcare service | No qualifying provider/function is established for Alex's installation. No reliance proposed. |
| Small size, free access, Finland location or approval-only accounts | These are context/risk factors, not a demonstrated Schedule 1 exemption. |

Review the current [Schedule 1](https://www.legislation.gov.uk/ukpga/2023/50/schedule/1?view=plain)
before adopting an exemption. Its paragraph 7 conditions and paragraph 8 partial
service rules require actual operating evidence. No provider pornography offering
has been established; any future such content requires a separate scope assessment.

## UK links: confirmed audience and working decision

Section 4 considers significant UK users, UK targeting, or UK accessibility with
reasonable grounds for a material risk of significant harm to people in the UK.
Finland hosting/operation does not settle these tests. UK source material or English
text alone is not proof of UK targeting, and internet accessibility alone does not
establish the significant-harm limb. [Section 4](https://www.legislation.gov.uk/ukpga/2023/50/section/4),
[Ofcom regulation checker](https://www.ofcom.org.uk/os-toolkit/regulation-checker/regulation-checker).

Alex's dated confirmation establishes that UK users are part of the permitted
audience. It is not, alone, a count of significant UK usage, proof of targeting or
evidence satisfying the significant-harm limb. Do not turn admitted UK access into
an unsupported legal finding, or treat Finland operation as excluding regulation.

The working decision is to plan and assess on a regulated-service basis now,
including the possible search component. KAN-246 records the remaining private
evidence: UK availability/entry-into-scope dates, proportionate audience evidence,
targeting and harm facts, exemption/search analysis, and legal advice if needed.
Any later out-of-scope conclusion needs its own dated reasons and evidence. The
absence of inspected incidents is not proof of no incidents. Do not collect
identity documents or intrusive tracking merely to populate this assessment.

The first-assessment deadline depends on actual entry into scope. The current date
does not restart a past deadline. [Ofcom's current duties guidance](https://www.ofcom.org.uk/online-safety/illegal-and-harmful-content/illegal-content-duties-under-the-online-safety-act)
explains assessment, protective measures and record/review duties. No historical
compliance date is certified by this document.

## Reporting, complaints and responsibility

The existing public terms direct misuse/access concerns to **alexorr@yahoo.co.uk**.
Alex is the named proposed accountable operator. A privacy-specific complaints
procedure exists separately. A generic mailbox is not evidence of a functioning
content complaint, moderation-appeal or timely response process. No dedicated
content-report/case/appeal endpoint was found, but such an API is not declared
universally mandatory: an accessible, adequately resourced manual process may be
appropriate after review.

Proposed procedure for approval and publication through KAN-188:

1. Accept reports from affected people, including people without accounts. Ask for
   a safe record reference/URL, concern and desired outcome; do not request copies
   of suspected illegal imagery, credentials or another person's private dossier.
2. Keep a private case reference, receipt time, owner, urgency and proportionate
   evidence. Escalate credible immediate danger appropriately; preserve only what
   can lawfully be held. Do not forward suspected illegal material casually.
3. Check context, jurisdiction, applicable law, access and content identity. Apply
   necessary supported restrictions/removal promptly, with reasons. Distinguish
   lawful reporting/research about wrongdoing from illegal encouragement or material.
4. Notify the reporter and affected user of the decision where lawful and safe;
   provide a route to challenge moderation/access decisions. Where practicable,
   obtain a fresh reviewer; disclose when the small operator has no independent one.
5. Record review outcome, remedy, response time and necessary retention/hold. Review
   trends and whether measures actually worked. Protect privacy and expression;
   preserve lawful content and explain limitations instead of promising blanket removal.

This is a prepared procedure, not a claim of new public commitments, case handling
or external messages. KAN-188 owns the full terms/AUP, accessible published process
and acceptance controls. No fixed legal response deadline is invented here.

## Measures, follow-ups and review triggers

| Owner / work | Deliverable and status |
| --- | --- |
| Alex / KAN-189 | Completed 18 October 2026: approved this dated assessment record and conservative working scope, retaining its evidence limits and the follow-ups below. |
| Operator validation / [KAN-246](https://alex-orr.atlassian.net/browse/KAN-246) | Promptly establish the actual UK availability dates and applicable deadlines, final territorial/search/exemption and children-access conclusions, current deployment/complaints evidence and applicable Ofcom measures. Verify reporting/removal/appeal effectiveness and record any resulting children's risk assessment and protective measures. The annual review date does not defer an existing duty. |
| Claude queue / [KAN-188](https://alex-orr.atlassian.net/browse/KAN-188) | Complete full terms/AUP and acceptance, plus accessible reporting/complaints/appeal procedure. Historical 18+ and governing-law assumptions need review; current source contains no age rule/assurance. |
| Unassigned follow-up / [KAN-245](https://alex-orr.atlassian.net/browse/KAN-245) | Permit authorised harmful-post removal while a team stays archived. Current board moderation rejects archived-team writes despite continued readability. Preserve ordinary read-only status, permissions, audit and revision guards. |
| Alex / children's assessment, tracked in KAN-246 | If the service is likely accessed by children, including the statutory default after a missed first access-assessment deadline or an Ofcom determination, complete a children's risk assessment and applicable protective measures. Existing access can trigger duties without intentional expansion. Establish actual scope/deadlines promptly. Do not treat an 18+ rule or approval as highly effective age assurance. Duplicate-check and ticket any newly confirmed engineering gap. |
| Existing privacy/AI work | KAN-185 addresses privacy, KAN-191 AI labelling. Neither replaces illegal-content assessment or operating measures. |

Reassess before public sharing, open sign-up, public profiles, broader invitations,
new communication/search/recommendation capabilities, new audiences or a change in
provider/control. Also review after relevant incidents, complaints, new evidence
of children/UK use, and significant guidance/risk-profile changes. Review this
record at least annually, next routine date **16 October 2027**, sooner if any
trigger occurs. Keep dated private evidence and a non-sensitive decision summary.

**Approval record, 18 October 2026:** Alex explicitly approved the assessment-record
and PR #211 merge request. Approval adopts the conservative regulated-service
working scope for planning and retains the unresolved legal, children-access and
operating follow-ups in KAN-246, KAN-188 and KAN-245. It does not certify statutory
compliance, establish effective age assurance or approve a manual production
rollout. No production setting or public policy was changed by this assessment.
