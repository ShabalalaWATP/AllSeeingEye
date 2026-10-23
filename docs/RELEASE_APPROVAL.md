# Production release approval

KAN-225's explicit approval gate was applied on 11 October 2026 after Alex
approved the exact settings and two harmless verification runs. The live
`production` environment now requires approval before `Deploy VPS` can run.
See the [verified settings and test outcomes](reviews/2026-10-11-KAN-225-live-gate.md).
The checked-in payload does not apply itself; later configuration changes still
require the applicable approval.

## Verified settings

Require `ShabalalaWATP` (verified GitHub user ID `128953080`) to approve each
production job. Retain the existing selected-branch policy, whose only allowed
branch is `main`. Disable **Allow administrators to bypass configured protection
rules** in the environment settings.

Keep **Prevent self-review** disabled for the current single-maintainer setup:
Alex can approve a release initiated through the same account. Enabling it would
require another reviewer when Alex triggers the run. This provides an explicit
release decision, not a guarantee of independent approval by a second person.
Agents must not approve a run merely because its checks passed.

Repository administrators can still edit these settings. Credentials acting as
Alex have Alex's authority; this gate does not distinguish a human from an agent
using those credentials. Restrict credential access and retain the recorded
release approval. Existing main-branch review and CI requirements remain intact.

## Apply or restore after approval

1. Check there are no active or pending production jobs. Record the current
   environment settings and deployment branch rules for recovery.
2. Confirm the reviewer account and repository match this installation. Apply
   `infra/github/production-review.json` with:

   ```sh
   gh api --method PUT repos/ShabalalaWATP/AllSeeingEye/environments/production \
     --input infra/github/production-review.json
   ```

3. In **Settings, Environments, production**, disable administrator bypass and
   save. The documented REST request schema does not expose that switch, so do
   not assume a successful payload update changed it.
4. Read the environment and branch rules back. Require the reviewer above,
   `can_admins_bypass: false`, selected-branch restrictions and exactly the `main`
   branch rule. Preserve secrets and variables; do not delete the environment.
5. Record the setting change and verification in KAN-225. If a later change
   requires removing the gate, obtain a separate approval rather than silently
   reverting it when a deployment waits.

## Check the gate without a production deployment

The **Release approval gate check** workflow contains only a summary message.
It uses no secrets, checkout, external action or deployment command. Its addition
still follows normal reviewed merge approval. Never use **Deploy VPS** as a
harmless gate test.

After this workflow is on `main`, dispatch it manually from `main`. Verify its
job waits for review and has not executed the summary step. Approve that check
as Alex and confirm the summary is written. Dispatch a second check and reject
it; confirm the summary step never runs. Record both run URLs and conclusions.
These checks create GitHub deployment records for the environment but do not
contact or change the production host.

The initial acceptance is complete: both jobs first waited without executing a
step, the approved check succeeded and wrote its summary, and the rejected check
failed with no executed steps. Repeat this procedure when an authorised change
requires fresh verification; the previous approval does not authorise future runs.

## Actual releases

Before approving **Deploy VPS**, inspect the tested SHA, CI results, migrations,
backup and recovery plan, and any manual rollout requirements. An approval may
wait behind another release; the controller still rechecks current `main` before
cutover. Reject superseded or unapproved work. Environment approval does not
replace the restricted SSH controller, its protected-path checks or health checks.

References, checked 9 October 2026:
[GitHub environment configuration](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments),
[protection rules](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
and [environment REST API](https://docs.github.com/en/rest/deployments/environments#create-or-update-an-environment).
