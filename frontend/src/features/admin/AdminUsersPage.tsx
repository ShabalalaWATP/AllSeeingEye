import { useCallback, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { LinkReveal } from '@/components/ui/LinkReveal';
import { Table, Th } from '@/components/ui/Table';
import { listUsers } from '@/lib/api/admin';
import { describeError } from '@/lib/api/errors';
import type { ResetLinkResponse, User } from '@/lib/api/schemas';
import { useResource } from '@/lib/hooks/useResource';

import { UserRow } from './UserRow';

interface ResetIssue {
  email: string;
  response: ResetLinkResponse;
}

export default function AdminUsersPage() {
  const { data, error, loading, setData } = useResource(listUsers);
  const [resetIssue, setResetIssue] = useState<ResetIssue | null>(null);

  const replace = useCallback(
    (updated: User) => {
      setData((current) =>
        current === null ? current : current.map((item) => (item.id === updated.id ? updated : item)),
      );
    },
    [setData],
  );

  return (
    <section className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <h1 className="text-xl font-semibold">Users</h1>
      {resetIssue === null ? null : (
        <LinkReveal
          title={`Reset link for ${resetIssue.email}`}
          link={resetIssue.response.reset_link}
          expiresAt={resetIssue.response.expires_at}
        />
      )}
      {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
      {data === null ? (
        loading ? (
          <LoadingNote label="Loading users" />
        ) : null
      ) : (
        <Table caption="Users">
          <thead>
            <tr>
              <Th>User</Th>
              <Th>Role</Th>
              <Th>Active</Th>
              <Th>Last sign in</Th>
              <Th>Actions</Th>
            </tr>
          </thead>
          <tbody>
            {data.map((user) => (
              <UserRow
                key={user.id}
                user={user}
                onUpdated={replace}
                onResetLink={(response) => {
                  setResetIssue({ email: user.email, response });
                }}
              />
            ))}
          </tbody>
        </Table>
      )}
    </section>
  );
}
