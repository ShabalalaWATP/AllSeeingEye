# Processing and retention records

These records describe Alex Orr's personal All Seeing Eye installation, operated
from Finland. They also provide a reusable technical inventory for other operators,
who must replace the installation facts and assess their own purposes and recipients.

| Record                                                   | Purpose                                                                    |
| -------------------------------------------------------- | -------------------------------------------------------------------------- |
| [Processing register](PROCESSING_REGISTER.md)            | People, data, purposes, recipients, safeguards and linked retention rules. |
| [Processors and transfers](PROCESSORS_AND_TRANSFERS.md)  | Provider roles, agreement evidence, locations and transfer safeguards.     |
| [Retention schedule](RETENTION_SCHEDULE.md)              | Enforced expiry, deletion triggers, manual duties and implementation gaps. |
| [AI region and residency guide](../AI_DATA_RESIDENCY.md) | Configuration steps and the limits of regional AI routing.                 |

Record owner: **Alex Orr**, contact **alexorr@yahoo.co.uk**. Review date:
**14 October 2026**. Review continued need at least quarterly, next due
**14 January 2027**, and on changed purposes, providers, deployment, account closure
or a rights request. The date is an operating duty, not an installed reminder.
No DPO or separate representative appointment is recorded in the evidence reviewed.

Evidence has different scopes:

- **Operator-confirmed, 14 October:** Finland; Hetzner DPA recorded; standard
  OpenAI/Resend terms with no opt-ins or custom settings. Agreement copies and
  account screens were not independently audited or published.
- **Observed, 11 October:** running revision `13efceef`, Helsinki hosting,
  OpenAI and Resend, enabled archive/push configuration, backup/log configuration.
  See the [dated installation record](../PUBLIC_POLICY_REVIEW.md). Configuration
  does not prove a particular message, research task or capture occurred.
- **Code reviewed, 14 October:** `14a65442`, based on main `905aace7`. Backend
  behaviour is identical between those revisions. Later features such as idle
  session tracking and enquiries were not verified on the observed live release.
- **Conditional:** an optional integration or user choice. It is not asserted to
  be active merely because the code supports it.
- **Unresolved:** assessment or implementation work explicitly linked below.

These are KAN-187's records, not a completed DPIA, legal opinion or certification.
The [privacy notice](../../frontend/src/features/public-policy/privacy.json)
uses EU/Finnish context and states the personal-installation scope without claiming
a universal household exemption. Purpose-specific lawful bases, special-category
and offence-data conditions, indirect notice and residual-risk decisions remain
under [KAN-185](https://alex-orr.atlassian.net/browse/KAN-185). Its restricted working
assessment contains no public host-access details here. Do not collect extra
sensitive data merely to fill a register.

Maintain the records alongside code and deployment changes. Keep private contract
references, assessment evidence, rights cases and deletion decisions in protected
operator records. Record decisions and reasons, never credentials or copies of
research inputs in Jira. The [personal-data procedure](../PERSONAL_DATA_OPERATIONS.md)
explains supported controls and their limits. Unimplemented deletion is tracked in
KAN-238 through KAN-243; documentation does not itself execute those operations.
