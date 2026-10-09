# Idle session expiry

The default idle limit is three hours. Set `ASE_SESSION_IDLE_MINUTES` between
5 and 1440 minutes to change it. `ASE_ADMIN_SESSION_IDLE_MINUTES` optionally
sets a separate limit for administrators, with the same bounds. Unset inherits
the general limit. Policy applies using the current account role and server time.

Successful sign-in, including completed MFA, starts an activity record for the
refresh family. Refresh token rotation does not change it. Explicit activity can
advance it at most once per minute across all tabs and process restarts. The
browser sends a bearer-bound, CSRF-protected heartbeat after actual interaction.
Background polling, automatic refresh and open streams remain passive. A caller
cannot revive a family by submitting activity after its deadline.

The browser uses server-confirmed activity and clock offset for its advisory
countdown. It observes trusted pointer, keyboard, touch, wheel and focus events,
with throttled mouse movement. Scroll counts only after a recent trusted gesture,
so programmatic scrolling cannot keep a session alive. Tabs share confirmed family activity
through BroadcastChannel where available. Without it, each tab relies on its own
server responses. Nothing is written to localStorage or sessionStorage.

An accessible warning offers **Stay signed in** and **Sign out** five minutes
before the idle deadline. Its announced countdown changes no more than once per
minute. At the minimum five-minute policy, the warning waits for one minute of
inactivity and shows four minutes remaining. This also applies after Stay, so
the dialog does not immediately reopen. While the dialog is open, its explicit
Stay control records activity; moving focus between its choices does not.

Expiry clears in-memory authentication and private drafts, ends streams and
returns to sign-in with the current route retained. The message describes the
configured idle duration and warns that unsaved drafts were lost. A logout
request names the original family, preventing replaced shared cookies from
signing out another session. Countdown expiry requests conditional logout: the
server returns the current deadline without mutation if another tab has kept the
family active. A suspended tab or missed BroadcastChannel message cannot revoke
that live family. Explicit **Sign out** remains unconditional. If expiry cannot be
confirmed because the API is unavailable, the blocking warning reports the failure
and retries no sooner than one minute later. Verification requests time out after
ten seconds; they do not delay an explicit sign-in or Sign out. Protected server
operations still enforce the idle deadline.

Conditional expiry never sends cookie mutations, including after revocation. This
prevents a delayed response from clearing cookies from a later login in another
tab. A retained revoked refresh cookie is rejected on its next use and replaced
by the next successful sign-in. Explicit Sign out still clears its session cookies.

Server enforcement remains authoritative with JavaScript disabled or a modified
client. Protected requests and release fences reject an expired family. A cached
release check cannot outlive its observed idle deadline; another tab's accepted
heartbeat can be recognised by a fresh check. Streams recheck within
`ASE_SESSION_RECHECK_SECONDS`, then emit `access.changed` and end. Push admission
and delivery also require an active, non-idle family.

Passive checks do not commit database writes. The next refresh, heartbeat or
logout transaction performs durable family revocation, push registration cleanup
and one `session.idle_expired` audit transition. This preserves transaction
ownership when a protected operation has pending business writes. It does not
promise an audit event for an abandoned browser that never contacts the server
again after expiry.

## Rollout

Migration `0092`, after `0091`, creates `refresh_family_activity` and backfills
one row per existing family at the migration's server timestamp. Existing
sessions receive one configured idle grace period from rollout; old rotation
timestamps are not treated as human activity. Existing revocation tombstones
remain authoritative. A missing family activity row fails closed.

Back up the intended database and follow the existing controlled migration
workflow before deploying the new API. Run `uv run ase migrate` only with the
explicitly verified target database configuration. Development verification uses
fresh temporary databases; it does not migrate an operator database. A downgrade
removes activity state and must not be used as a way to retain idle enforcement.

There is no new absolute session lifetime. The existing refresh-token expiry
still applies. Any absolute lifetime is a separate policy decision requiring
approval and follow-up work.
