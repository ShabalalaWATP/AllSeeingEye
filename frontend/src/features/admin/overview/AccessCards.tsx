import { StatusPill } from '@/components/admin/StatusPill';
import { listPendingAccountRequests, listUsers } from '@/lib/api/admin';
import { fetchMfaStatus, type MfaMethod } from '@/lib/api/mfa';
import { listTeams } from '@/lib/api/teams';
import { formatAgo } from '@/lib/format';
import { useNow } from '@/lib/hooks/useNow';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

import { Figure, OverviewCard, StatList } from './OverviewCard';
import { summariseTeams, summariseUsers } from './overviewSummaries';

const loadPeople = () => Promise.all([listUsers(), listTeams()]);

export function RequestsCard() {
  const resource = useScopedResource(listPendingAccountRequests);
  const now = useNow();
  return (
    <OverviewCard title="Account requests" to="/admin/requests" icon="requests" resource={resource}>
      {(requests) => (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Figure
              value={requests.length}
              caption={requests.length === 1 ? 'pending request' : 'pending requests'}
              tone={requests.length > 0 ? 'text-amber' : 'text-text'}
            />
            {requests.length === 0 ? (
              <StatusPill tone="good">Queue clear</StatusPill>
            ) : (
              <StatusPill tone="warning">Awaiting decision</StatusPill>
            )}
          </div>
          {requests.length === 0 ? (
            <p className="mt-3 text-sm text-muted">No one is waiting for account access.</p>
          ) : (
            <ul className="mt-3 divide-y divide-line/60 border-t border-line/60">
              {[...requests]
                .sort((a, b) => b.created_at.localeCompare(a.created_at))
                .slice(0, 3)
                .map((request) => (
                  <li key={request.id} className="flex items-center justify-between gap-3 py-2">
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium">
                        {request.display_name}
                      </span>
                      <span className="block truncate text-xs text-muted">{request.email}</span>
                    </span>
                    <span className="shrink-0 font-mono text-[11px] text-muted">
                      {formatAgo(request.created_at, now)}
                    </span>
                  </li>
                ))}
            </ul>
          )}
        </>
      )}
    </OverviewCard>
  );
}

export function PeopleCard() {
  const resource = useScopedResource(loadPeople);
  return (
    <OverviewCard
      title="Users"
      to="/admin/users"
      icon="users"
      resource={resource}
      related={{ to: '/admin/teams', label: 'Teams' }}
    >
      {([users, teams]) => {
        const people = summariseUsers(users);
        const groups = summariseTeams(teams);
        return (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Figure value={people.active} caption="active accounts" />
              {people.admins <= 1 ? (
                <StatusPill tone="warning">
                  {people.admins === 1 ? 'One active administrator' : 'No active administrator'}
                </StatusPill>
              ) : (
                <StatusPill tone="good">{people.admins} administrators</StatusPill>
              )}
            </div>
            <StatList
              items={[
                { label: 'Administrators', value: people.admins },
                { label: 'Inactive', value: people.inactive },
                { label: 'Never signed in', value: people.neverSignedIn },
              ]}
            />
            <p className="mt-3 border-t border-line/60 pt-3 text-sm text-muted">
              {groups.total === 0
                ? 'No teams yet.'
                : `${groups.active} active ${groups.active === 1 ? 'team' : 'teams'}${groups.archived > 0 ? `, ${groups.archived} archived` : ''}.`}
            </p>
          </>
        );
      }}
    </OverviewCard>
  );
}

const METHOD_LABELS: Record<MfaMethod, string> = {
  authenticator: 'Authenticator app',
  email: 'Email code',
  recovery: 'Recovery codes',
};

export function SecurityCard() {
  const resource = useScopedResource(fetchMfaStatus);
  return (
    <OverviewCard title="Security" to="/admin/security" icon="security" resource={resource}>
      {(status) => (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Figure
              value={status.methods.length}
              caption={status.methods.length === 1 ? 'factor enrolled' : 'factors enrolled'}
            />
            {status.methods.length > 0 ? (
              <StatusPill tone="good">Protected</StatusPill>
            ) : (
              <StatusPill tone="warning">No factor enrolled</StatusPill>
            )}
          </div>
          <p className="mt-3 text-sm text-muted">
            Your own sign-in protection. Administrator sessions must pass multi-factor verification
            before this workspace opens.
          </p>
          <ul aria-label="Enrolled factors" className="mt-3 flex flex-wrap gap-1.5">
            {status.methods.length === 0 ? (
              <li className="text-sm text-muted">No factors enrolled.</li>
            ) : (
              status.methods.map((method) => (
                <li key={method}>
                  <StatusPill tone="info" icon="key">
                    {METHOD_LABELS[method]}
                  </StatusPill>
                </li>
              ))
            )}
          </ul>
        </>
      )}
    </OverviewCard>
  );
}
