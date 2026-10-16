# Codex assigned-ticket delivery queue

Alex requested completion of all Codex-assigned tickets, starting with KAN-244.
The Jira query on 16 October confirmed eleven individual tickets plus parent
epic KAN-216. Assignment and status are verified in Jira; this record is a delivery
guide, not automatic closure or release approval.

| Order | Ticket | Outcome | Current evidence |
| --- | --- | --- | --- |
| 1 | [KAN-244](https://alex-orr.atlassian.net/browse/KAN-244) | Native image advisory triage and bounded parser mitigations | [PR 204](https://github.com/ShabalalaWATP/AllSeeingEye/pull/204), merged as `9d5a0166`, Jira Done; unresolved native paths remain explicit |
| 2 | [KAN-242](https://alex-orr.atlassian.net/browse/KAN-242) | SQLite alert/outbox deletion parity | Current implementation, disposable SQLite/PostgreSQL verification |
| 3 | [KAN-238](https://alex-orr.atlassian.net/browse/KAN-238) | Expired authentication and decided-request cleanup | To do |
| 4 | [KAN-239](https://alex-orr.atlassian.net/browse/KAN-239) | Audit, model usage and terminal-delivery retention | To do |
| 5 | [KAN-241](https://alex-orr.atlassian.net/browse/KAN-241) | Cleanup independent of dormant/disabled workloads | To do |
| 6 | [KAN-240](https://alex-orr.atlassian.net/browse/KAN-240) | Dependency-aware account and saved-work removal | To do |
| 7 | [KAN-243](https://alex-orr.atlassian.net/browse/KAN-243) | Recovery reconciliation and external-copy review | To do |
| 8 | [KAN-185](https://alex-orr.atlassian.net/browse/KAN-185) | Finnish/EU privacy assessments | To do, with operator/legal decisions kept distinct from technical evidence |
| 9 | [KAN-189](https://alex-orr.atlassian.net/browse/KAN-189) | UK Online Safety Act scope assessment | To do |
| 10 | [KAN-191](https://alex-orr.atlassian.net/browse/KAN-191) | Visible and machine-readable AI labels | To do |
| 11 | [KAN-192](https://alex-orr.atlassian.net/browse/KAN-192) | Configured public security.txt | To do |

The alert-deletion parity repair precedes the broader retention work because it
establishes the correct dependent-row behaviour. Retention and recovery controls
inform the assessments. One primary implementation runs at a time, with isolated
worktrees and read-only focused review. Dependent branches must record their base
explicitly; neither shared local changes nor another contributor's PR is overwritten.

Each implementation needs relevant local checks, full required CI, independent
review and authorised integration before Done. A merge to main can start a
production deployment, so release approval is separate. No task authorises a
production purge, invented legal sign-off, licence adoption or blanket acceptance
of dependency vulnerabilities.
