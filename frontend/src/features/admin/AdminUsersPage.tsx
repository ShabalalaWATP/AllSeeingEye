import { useCallback, useState } from 'react';

import { AdminIcon } from '@/components/admin/AdminIcon';
import { AdminPage, AdminSection, EmptyState } from '@/components/admin/AdminPage';
import { StatusPill } from '@/components/admin/StatusPill';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { LinkReveal } from '@/components/ui/LinkReveal';
import { Table, Th } from '@/components/ui/Table';
import { listUsers } from '@/lib/api/admin';
import { describeError } from '@/lib/api/errors';
import type { ResetLinkResponse, User } from '@/lib/api/schemas';
import { getAdminResearchUsage, type UserResearchAllowance } from '@/lib/api/researchUsage';
import { useResource } from '@/lib/hooks/useResource';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

import { summariseUsers } from './overview/overviewSummaries';
import { UserRow } from './UserRow';

interface ResetIssue {
  email: string;
  response: ResetLinkResponse;
}

/** Case-insensitive match on name, email or role; filtering never changes server data. */
export function matchesUser(user: User, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (needle === '') return true;
  return [user.display_name, user.email, user.role].some((value) =>
    value.toLowerCase().includes(needle),
  );
}

export default function AdminUsersPage() {
  const { data, error, loading, setData, reload } = useResource(listUsers);
  const allowances = useScopedResource(getAdminResearchUsage);
  const [resetIssue, setResetIssue] = useState<ResetIssue | null>(null);
  const [query, setQuery] = useState('');
  const replaceAllowance = (updated: UserResearchAllowance) => {
    allowances.setData(
      (current) =>
        current && {
          ...current,
          items: current.items.map((item) => (item.user_id === updated.user_id ? updated : item)),
        },
    );
  };

  const replace = useCallback(
    (updated: User) => {
      setData((current) =>
        current === null
          ? current
          : current.map((item) => (item.id === updated.id ? updated : item)),
      );
    },
    [setData],
  );
  const summary = data === null ? null : summariseUsers(data);
  const visible = data?.filter((user) => matchesUser(user, query)) ?? [];

  return (
    <AdminPage
      eyebrow="Access and teams"
      title="Users"
      description="Manage account roles, research levels and active access. You can change your own research level, but not your own role or active status."
      meta={
        summary === null ? undefined : (
          <ul aria-label="Account totals" className="flex flex-wrap gap-1.5">
            <li>
              <StatusPill tone="good">{summary.active} active</StatusPill>
            </li>
            <li>
              <StatusPill tone="info" icon="security">
                {summary.admins} administrators
              </StatusPill>
            </li>
            <li>
              <StatusPill tone="neutral">{summary.inactive} inactive</StatusPill>
            </li>
          </ul>
        )
      }
      actions={
        <Button
          variant="secondary"
          busy={loading || allowances.loading}
          onClick={() => {
            void reload();
            void allowances.reload();
          }}
        >
          <AdminIcon name="refresh" size={16} />
          Refresh
        </Button>
      }
    >
      {resetIssue === null ? null : (
        <LinkReveal
          title={`Reset link for ${resetIssue.email}`}
          link={resetIssue.response.reset_link}
          expiresAt={resetIssue.response.expires_at}
        />
      )}
      {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
      {allowances.error && (
        <Alert tone="error">
          {describeError(allowances.error)}{' '}
          <Button variant="ghost" onClick={() => void allowances.reload()}>
            Retry research allowances
          </Button>
        </Alert>
      )}
      <p className="text-sm text-muted">
        Research levels count manual and subscription runs together. New accounts start at Level 1.
        Browsing, map tools and feed refreshes do not count. Daily limits reset at midnight UTC;
        weekly limits reset on Monday at midnight UTC. AI provider and token budgets still apply to
        every level.
      </p>
      <AdminSection
        title="Accounts"
        icon="users"
        actions={
          data === null || data.length < 2 ? undefined : (
            <div className="w-full sm:w-64">
              <TextField
                label="Filter accounts"
                labelHidden
                type="search"
                placeholder="Filter by name, email or role"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </div>
          )
        }
      >
        {data === null ? (
          loading ? (
            <LoadingNote label="Loading users" />
          ) : null
        ) : visible.length === 0 ? (
          <EmptyState icon="users" title="No accounts match this filter.">
            Clear the filter to see every account.
          </EmptyState>
        ) : (
          <Table caption="Users" stickyHeader>
            <thead>
              <tr>
                <Th>User</Th>
                <Th>Role</Th>
                <Th>Active</Th>
                <Th>Research allowance</Th>
                <Th>Last sign in</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {visible.map((user) => (
                <UserRow
                  key={user.id}
                  user={user}
                  onUpdated={replace}
                  allowance={allowances.data?.items.find((item) => item.user_id === user.id)}
                  tiers={allowances.data?.tiers ?? []}
                  allowanceLoading={allowances.loading}
                  onAllowanceUpdated={replaceAllowance}
                  onAllowanceReload={allowances.reload}
                  onResetLink={(response) => {
                    setResetIssue({ email: user.email, response });
                  }}
                />
              ))}
            </tbody>
          </Table>
        )}
      </AdminSection>
    </AdminPage>
  );
}
