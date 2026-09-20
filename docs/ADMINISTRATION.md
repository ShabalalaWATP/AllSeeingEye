# Administration

Administrators use a dedicated workspace at `/admin`. It has its own overview,
navigation and mobile menu. A normal administrator sign-in starts there; a saved
deep link still opens its requested page. Use **Return to research** to enter the
research interface. Only authenticated, active administrators see its entry.

| Area | Purpose |
| --- | --- |
| Account requests | Review applications and approve or reject access |
| Users | Manage roles, active status and reset links |
| Teams | Create teams, maintain membership and archive teams |
| AI connections | Configure, test and apply global or team model connections |
| Sources | Inspect collector health and reset failed sources |
| Audit log | Review recorded actions and their actors |
| Security | Manage authenticator protection for your own administrator account |

The overview is a directory of actual controls, not a dashboard of estimated or
synthetic operational statistics. Team sharing remains available in research;
its ordinary member and designated-manager permissions are unchanged.

## Current access

The entire administrator shell is protected before its pages mount. Users and
team managers cannot open administrator pages or use administrator APIs by typing
their URLs. Server checks use current account and session state.

The client verifies the current session on entry, window focus and every 30 seconds
while visible. Initial verification hides administrator content until confirmed.
A failed check hides it with retry and return-to-research actions. Delayed results
from an earlier session cannot restore its access or sign out a newer account.
These verification calls do not silently refresh an expired token: an expired
administrator session returns to sign-in. This is periodic checking, not immediate
revocation pushed to every open browser.

Activation and reset-link responses recheck current administrator access after
their authorised action commits. Revocation prevents release of the link without
undoing a completed approval. See the [scoped access review](security/ADMIN_WORKSPACE_REVIEW.md).

For provider setup, see [AI connections](AI_CONNECTIONS_OPERATIONS.md).

## Source controls and health

A successful sampled collection counts as live and shows its coverage warning.
Failed requests and unsuccessful refreshes remain degraded, even when retained
data can still be displayed. The last error is failure history, not a coverage
statement. Check the last successful poll and the dates of the actual observations.

Changing a source switch reloads the full list of effective settings. Parent
controls can affect related sources, while explicit child overrides remain in
force. If the reload fails, retry before relying on the displayed state.

The first AI connection must be assigned as the global default. Team and personal
assignments become available after that default exists.
