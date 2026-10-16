# Online safety: provisional risk and children's access record

**16 October 2026. Owner: Alex Orr. Approval and operating evidence pending.**
Read with [scope](ONLINE_SAFETY.md) and [source evidence](ONLINE_SAFETY_EVIDENCE.md).
This completes the desk assessment, not an assurance that statutory operating
duties are met. It must be reconciled with actual users, complaints, incidents,
source/search configuration and effectiveness of moderation before a final result.

## 1. Features and risk factors

We used Ofcom's four-step approach and considered the user-to-user/search factors
in [risk guidance v2.0](https://www.ofcom.org.uk/siteassets/resources/documents/online-safety/information-for-industry/illegal-harms/updates/risk-assessment-guidance-and-risk-profiles.pdf),
including closed groups, profiles, comments, images, location, reposting, links and
search. This is a mapping to this app, not a reproduced Ofcom score or endorsement.

Present: group boards/replies, opted-in profiles/avatars, team report copies,
annotations/maps, selected links and saved-content search (S1-S8/S14). Invitation
notes are a limited directed-message surface (S7). There is no verified unrestricted
one-to-one chat, user livestream publishing, end-to-end encrypted messaging,
marketplace or user-follow recommendation graph in the reviewed surface. Research
AI/planning can amplify source content; external video/web queries need separate
search-component attention (S12-S13). No commercial advertising incentive is
established for the current personal installation. These absences reduce some
routes but cannot eliminate misuse of general text, images or links.

Alex confirmed approved adult users, including UK users, on 16 October 2026 (O1).
Unknowns: independent age/location evidence, user counts, frequency of shared work,
incident reports, moderation response times, subject populations and deployment.
No reviewed complaints is not evidence of no complaints. Closed groups may reduce
reach but also hide harmful activity. Operator-approved accounts are not proof of
trusted conduct, verified identity or age.

## 2. Harm assessment

These are provisional engineering judgements for the described features. **Low**
means a less direct route in this design, not negligible harm; **medium** means a
credible route requiring measures/evidence; **high** means directly enabled misuse
or serious uncertainty requiring priority action. Impact can be severe in every
row. No empirical incident rate or final Ofcom risk-level-table result is claimed.
Common controls: scoped access, account admission/restriction, limited board
moderation and public misuse rules (S1/S3/S8-S11). Their current operation is unverified.

| Harm considered | Relevant app route and possible consequence | Provisional likelihood / impact / priority |
| --- | --- | --- |
| Terrorism | Research snippets, cited URLs and board discussion could disseminate prohibited material or encourage violence; legitimate reporting must be distinguished | Medium / severe / high |
| CSEA: grooming | Invitation notes, profiles and closed-team conversation could facilitate contact if minors gain access | Unknown child exposure, credible route / severe / high until evidence |
| CSEA: imagery | Avatars, selected images or shared report content could expose illegal imagery; parser safety is not content moderation | Medium / severe / high |
| CSEA: URLs | A board, citation or external search result can direct users to illegal material without hosting the image | Medium / severe / high |
| Hate | User text or selectively repeated source claims may target protected groups | Medium / severe / high |
| Harassment, stalking, threats and abuse | Person/location research, mentions, profiles, maps and repeated posts provide a direct misuse route | High / severe / high |
| Controlling or coercive behaviour | Cross-source location/relationship inference or directed messages could aid control of another person | Medium / severe / high |
| Intimate-image abuse | Uploaded/selected imagery and shared reports may disclose or misrepresent private images | Medium / severe / high |
| Extreme pornography | Image/avatar surfaces and external links can expose material despite no adult-service purpose | Low-to-medium / severe / medium pending evidence |
| Sexual exploitation of adults | Private groups, location/identity information and invitations could facilitate targeting | Low-to-medium / severe / medium pending evidence |
| Human trafficking | Identity/location research and closed coordination could facilitate targeting or harmful disclosure | Low-to-medium / severe / medium pending evidence |
| Unlawful immigration offences | Research/location material or group posts could facilitate relevant offences; lawful migration reporting is not itself illegal | Low / serious-to-severe / medium |
| Fraud and financial services offences | Profile impersonation, misleading reports or links can deceive readers; no transaction feature is required | Medium / serious-to-severe / high |
| Proceeds of crime | Closed posts/links could facilitate transactions even without an app marketplace | Low / serious / medium |
| Drugs and psychoactive substances | General posts, links or queries may advertise/facilitate supply | Low / serious-to-severe / medium |
| Firearms, knives and other weapons | Source queries, links or group coordination can be misused | Low-to-medium / severe / medium pending evidence |
| Encouraging/assisting suicide or serious self-harm | Source material, AI summaries or board replies may expose or encourage harmful behaviour | Medium / severe / high |
| Foreign interference | Misleading sourced claims, synthetic analysis and coordinated closed groups could facilitate influence activity | Medium / serious-to-severe / high |
| Animal cruelty | User images/links, shared source material or requests may expose or encourage abuse | Low-to-medium / serious / medium |
| Cyberflashing | Directed invitation/profile/image surfaces or unsolicited shared material could expose recipients to sexual imagery | Low-to-medium / serious-to-severe / medium pending evidence |
| Other illegal content | Potential unlawful disclosure, computer misuse facilitation, impersonation or non-priority offences through research/text/link surfaces | Case-dependent / serious-to-severe / assess on report/source context |

The CSEA subrows are deliberately separate. This table covers the updated priority
categories without claiming that every distressing report, disputed statement or
lawful news reference is illegal. Determine the actual offence/context with the
appropriate legal judgement; retain minimal lawful evidence and protect expression.

Search-specific overlay: external news/video/web results can expose material even
when nobody posts it on a team board. Evaluate the provider/control boundary,
selected queries, result snippets/citations, ranking/AI amplification and downstream
disclosures. A provider's safety settings or an academic/research purpose does not
prove all returned results are safe. Internal saved-report search only changes the
discovery of already-visible records (S12-S14).

## 3. Measures, implementation and evidence

Priority measures are the actual-purpose/audience check, accessible reporting and
complaints process, prompt proportionate moderation/access restriction, archived
team removal fix, and documented review of child exposure. Existing tickets are
listed in ONLINE_SAFETY.md; KAN-188 owns public policy/acceptance and KAN-245 the
confirmed archived-board gap. KAN-246 tracks the operating evidence, deadline and
children's-duties validation. There is no blanket recommendation to scan private
messages, add age biometrics or buy a moderation service without evaluating need,
privacy, effectiveness and scope.

Before recording an in-scope compliance outcome, Alex must map the applicable
Ofcom codes to the actual service or document lawful alternative measures. Use the
[current regulatory index](https://www.ofcom.org.uk/online-safety/illegal-and-harmful-content/online-safety-regulatory-documents)
and distinguish codes in force from published amendments with later effective dates.
Then confirm
capacity for the process, run a synthetic reporting/removal/appeal exercise and
record timings/results. The desk findings and proposed process are not that exercise.
Emergency handling, legal evidence preservation and any mandatory external report
need an appropriate lawful route; this work did not transmit or inspect illegal content.

## Children's access assessment

**Stage one:** children cannot be excluded on the present evidence. No highly
effective age assurance was found. Current service rules do not even contain the
18+ statement anticipated by the ticket. Adding such a statement or relying on
administrator approval would not establish effective age assurance. The public
sign-in/policy pages and an account-request route also remain accessible.
[Ofcom children-access guidance](https://www.ofcom.org.uk/online-safety/illegal-and-harmful-content/childrens-access-assessment-duties-under-the-online-safety-act).

**Stage two:** the operator reports an approved adult audience. This is relevant
evidence of the intended admission policy, not independently verified ages or proof
of no child access. The research focus and gated accounts may reduce attraction/reach,
while an interactive globe, current events, aircraft,
space, maps and AI assistance may interest younger people. A non-commercial purpose
and no intended child audience do not settle likely access. There is no reliable
evidence here to conclude that the child-user condition is not met.

**Working outcome:** treat child access as possible and do not claim an adult-only
exemption. Alex must record proportionate existing audience evidence and likely
appeal, including parts of the service; no identity-document collection is proposed
just for this record. If likely accessed by children, complete the children's risk
assessment and applicable measures against the actual applicable deadlines. Duties
arising from existing access or a missed-assessment default cannot wait for an
intentional expansion to children. KAN-246 tracks this validation promptly.
If a negative stage-two conclusion is supported, record the evidence/reason/date
and repeat within 12 months or earlier trigger. Age assurance is one possible
control, not an automatic requirement chosen by this draft for every service.

**Deadline check:** if this installation is already in scope and has missed its
first children's access-assessment deadline, the statutory default treats it as
likely to be accessed by children. An Ofcom determination can also establish that
status. Check the actual entry-into-scope date and deadline; if either route applies,
record the resulting children's duties rather than leaving the outcome merely
possible/pending. A later completed assessment must support any changed conclusion.
This is a conditional rule, not a finding that this installation is in scope or
overdue. See [section 37(4)-(5)](https://www.legislation.gov.uk/ukpga/2023/50/section/37)
and [Ofcom guidance, paragraphs 2.34-2.36](https://www.ofcom.org.uk/siteassets/resources/documents/consultations/category-1-10-weeks/statement-protecting-children-from-harms-online/main-document/childrens-access-assessments-guidance.pdf).

## 4. Decision and review

Owner: Alex Orr. Approval: **pending**. The approved-adult/UK permitted audience is
confirmed; the conservative regulated-service working scope is proposed for approval.
Outstanding core evidence: UK-link details/dates, children's access outcome,
current deployment, complaints and moderation effectiveness,
applicable code measures or alternatives, and legal confirmation of search/exemption
boundaries. This conditional draft must not be represented as a final suitable and
sufficient statutory assessment while those material facts remain unresolved.

Keep case records privately and review measures after incidents/complaints, changed
features or audience, new child/UK evidence and revised guidance. Routine assessment
review is due 16 October 2027 at the latest; earlier triggers take precedence.
