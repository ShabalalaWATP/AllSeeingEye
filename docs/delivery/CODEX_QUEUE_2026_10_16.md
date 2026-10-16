# Codex assigned-ticket delivery queue

Alex requested completion of all Codex-assigned tickets, starting with KAN-244.
The Jira query on 16 October confirmed eleven individual tickets plus parent
epic KAN-216. Assignment and status are verified in Jira; this record is a delivery
guide, not automatic closure or release approval.

| Order | Ticket | Outcome | Current evidence |
| --- | --- | --- | --- |
| 1 | [KAN-244](https://alex-orr.atlassian.net/browse/KAN-244) | Native image advisory triage and bounded parser mitigations | [PR 204](https://github.com/ShabalalaWATP/AllSeeingEye/pull/204), merged as `9d5a0166`, Jira Done; unresolved native paths remain explicit |
| 2 | [KAN-242](https://alex-orr.atlassian.net/browse/KAN-242) | SQLite alert/outbox deletion parity | [PR 205](https://github.com/ShabalalaWATP/AllSeeingEye/pull/205), merged as `e1f36dcb`, Jira Done |
| 3 | [KAN-238](https://alex-orr.atlassian.net/browse/KAN-238) | Expired authentication and decided-request cleanup | [PR 206](https://github.com/ShabalalaWATP/AllSeeingEye/pull/206), merged as `7e594e38`, Jira Done; production enablement remains separate |
| 4 | [KAN-239](https://alex-orr.atlassian.net/browse/KAN-239) | Audit, model usage and terminal-delivery retention | [PR 207](https://github.com/ShabalalaWATP/AllSeeingEye/pull/207), implemented and tested, stacked after KAN-238 |
| 5 | [KAN-241](https://alex-orr.atlassian.net/browse/KAN-241) | Cleanup independent of dormant/disabled workloads | [PR 208](https://github.com/ShabalalaWATP/AllSeeingEye/pull/208), implemented and tested, stacked after KAN-239 |
| 6 | [KAN-240](https://alex-orr.atlassian.net/browse/KAN-240) | Dependency-aware account and saved-work removal | [PR 209](https://github.com/ShabalalaWATP/AllSeeingEye/pull/209), implemented and tested, stacked after KAN-241 |
| 7 | [KAN-243](https://alex-orr.atlassian.net/browse/KAN-243) | Recovery reconciliation and external-copy review | [PR 210](https://github.com/ShabalalaWATP/AllSeeingEye/pull/210), 35 stacked checks passed, after KAN-240 |
| 8 | [KAN-185](https://alex-orr.atlassian.net/browse/KAN-185) | Finnish/EU privacy assessments | Alex approved the restricted assessment record on 16 October; Jira Done, with exclusions and open legal/operational actions retained |
| 9 | [KAN-189](https://alex-orr.atlassian.net/browse/KAN-189) | UK Online Safety Act scope assessment | [PR 211](https://github.com/ShabalalaWATP/AllSeeingEye/pull/211), updated for operator-confirmed approved adults including UK users; assessment/release approval and refreshed CI pending; KAN-246 tracks operating validation |
| 10 | [KAN-191](https://alex-orr.atlassian.net/browse/KAN-191) | Visible and machine-readable AI labels | [PR 212](https://github.com/ShabalalaWATP/AllSeeingEye/pull/212), all 40 checks passed, merged as `8f4921ab`, Jira Done |
| 11 | [KAN-192](https://alex-orr.atlassian.net/browse/KAN-192) | Configured public security.txt | [PR 213](https://github.com/ShabalalaWATP/AllSeeingEye/pull/213), release approved; integrated image tests passed, refreshed full CI pending |

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
