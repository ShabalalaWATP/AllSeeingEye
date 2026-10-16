# Online safety scope and operating assessment

**16 October 2026, KAN-189. Owner: Alex Orr. Draft for operator/legal review.**

The reviewed application has user-to-user functionality. **An exemption and the
absence of UK links have not been established.** Assess the affected service on a
potentially regulated basis until the audience and territorial facts are resolved.
This is a reasoned working conclusion, not legal advice, certification or evidence
of completed operating duties. Alex's approval remains outstanding.

Baseline: main `e1f36dcb04c8dbdbe8945c756b0ac2747ae63ad3`. The
[source evidence](ONLINE_SAFETY_EVIDENCE.md) identifies actual features and limits.
The [risk assessment](ONLINE_SAFETY_RISKS.md) includes a separate children-access
analysis. Actual user locations/ages, service usage, complaints and moderation
outcomes have not been inspected. No private user records belong in this public file.

## Service boundary and users

This assessment concerns Alex's current personal installation, operated from
Finland, not every deployment of the public source repository. Account approval
and current team membership restrict access. Within those boundaries, users can
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

## UK links: unresolved facts and decision rule

Section 4 considers significant UK users, UK targeting, or UK accessibility with
reasonable grounds for a material risk of significant harm to people in the UK.
Finland hosting/operation does not settle these tests. UK source material or English
text alone is not proof of UK targeting, and internet accessibility alone does not
establish the significant-harm limb. [Section 4](https://www.legislation.gov.uk/ukpga/2023/50/section/4),
[Ofcom regulation checker](https://www.ofcom.org.uk/os-toolkit/regulation-checker/regulation-checker).

Alex must record privately the current/intended audience, whether UK users are
admitted or targeted, proportionate existing evidence of user locations, the date
of UK availability if applicable, and any credible UK harm evidence. Do not collect
identity documents or intrusive tracking simply to populate this assessment.

Proposed decision branches:

1. If a UK-link test is met and no applicable exemption is evidenced, treat the
   service as regulated and complete the relevant duties, including any search
   component. Resolve the current outstanding measures below before claiming compliance.
2. If reliable evidence supports no UK-link test, record the particular evidence,
   date and limits for an out-of-scope conclusion. The sharing features still exist;
   reassess before the audience or offering changes.
3. If facts remain unresolved, retain this conditional conclusion. No absence of
   incidents/users has been inferred from a lack of inspection.

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

| Owner / work | Outstanding deliverable |
| --- | --- |
| Alex / KAN-189 | Resolve audience/UK facts, final scope and children-access conclusion; verify current deployment, complaints evidence and relevant Ofcom measures; approve this dated record or record legal advice. |
| Claude queue / [KAN-188](https://alex-orr.atlassian.net/browse/KAN-188) | Complete full terms/AUP and acceptance, plus accessible reporting/complaints/appeal procedure. Historical 18+ and governing-law assumptions need review; current source contains no age rule/assurance. |
| Unassigned follow-up / [KAN-245](https://alex-orr.atlassian.net/browse/KAN-245) | Permit authorised harmful-post removal while a team stays archived. Current board moderation rejects archived-team writes despite continued readability. Preserve ordinary read-only status, permissions, audit and revision guards. |
| Alex / children's assessment | If the service is likely accessed by children, including the statutory default after a missed first access-assessment deadline or an Ofcom determination, complete a children's risk assessment and implement applicable protective measures. Establish the actual scope/deadline first. Do not treat an 18+ rule or approval as highly effective age assurance. A newly confirmed engineering gap requires a duplicate-checked ticket before expansion. |
| Existing privacy/AI work | KAN-185 addresses privacy, KAN-191 AI labelling. Neither replaces illegal-content assessment or operating measures. |

Reassess before public sharing, open sign-up, public profiles, broader invitations,
new communication/search/recommendation capabilities, new audiences or a change in
provider/control. Also review after relevant incidents, complaints, new evidence
of children/UK use, and significant guidance/risk-profile changes. Review this
record at least annually, next routine date **16 October 2027**, sooner if any
trigger occurs. Keep dated private evidence and a non-sensitive decision summary.

**Approval record:** pending Alex. This ticket remains open until its required
approval and relevant factual conclusion are recorded. No production setting or
public policy was changed by preparing this assessment.
