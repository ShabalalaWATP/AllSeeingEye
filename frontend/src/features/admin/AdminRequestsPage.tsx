import { useCallback, useState } from 'react';

import { AdminIcon } from '@/components/admin/AdminIcon';
import { AdminPage, AdminSection, EmptyState } from '@/components/admin/AdminPage';
import { StatusPill } from '@/components/admin/StatusPill';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { LinkReveal } from '@/components/ui/LinkReveal';
import { Table, Th } from '@/components/ui/Table';
import { listPendingAccountRequests } from '@/lib/api/admin';
import { describeError } from '@/lib/api/errors';
import type { ApproveResponse } from '@/lib/api/schemas';
import { formatUtc } from '@/lib/format';
import { useResource } from '@/lib/hooks/useResource';

import { AccountRequestRow } from './AccountRequestRow';

interface Approval {
  email: string;
  response: ApproveResponse;
}

export default function AdminRequestsPage() {
  const { data, error, loading, setData, reload } = useResource(listPendingAccountRequests);
  const [approval, setApproval] = useState<Approval | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const remove = useCallback(
    (id: string) => {
      setData((current) => (current === null ? current : current.filter((item) => item.id !== id)));
    },
    [setData],
  );

  return (
    <AdminPage
      eyebrow="Access and teams"
      title="Account requests"
      description="Review applications, approve account access with an initial role, or reject with an optional reason. Approval issues a single-use activation link."
      meta={
        data === null ? undefined : data.length === 0 ? (
          <StatusPill tone="good">Queue clear</StatusPill>
        ) : (
          <StatusPill tone="warning">{data.length} awaiting decision</StatusPill>
        )
      }
      actions={
        <Button variant="secondary" busy={loading} onClick={() => void reload()}>
          <AdminIcon name="refresh" size={16} />
          Refresh
        </Button>
      }
    >
      {approval === null ? null : approval.response.activation_link === null ? (
        <Alert tone="success">
          {approval.email} approved. The activation email has been sent and expires{' '}
          {formatUtc(approval.response.expires_at)}.
        </Alert>
      ) : (
        <LinkReveal
          title={`Activation link for ${approval.email}`}
          link={approval.response.activation_link}
          expiresAt={approval.response.expires_at}
        />
      )}
      {notice === null ? null : <Alert tone="info">{notice}</Alert>}
      {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
      <AdminSection
        title="Pending requests"
        icon="requests"
        description="Newest applications appear in the order they were received. Decisions take effect immediately."
      >
        {data === null ? (
          loading ? (
            <LoadingNote label="Loading requests" />
          ) : null
        ) : data.length === 0 ? (
          <EmptyState title="No pending requests.">
            New applications from the request account page will appear here.
          </EmptyState>
        ) : (
          <Table caption="Pending account requests" stickyHeader>
            <thead>
              <tr>
                <Th>Requester</Th>
                <Th>Reason</Th>
                <Th>Requested</Th>
                <Th>Decision</Th>
              </tr>
            </thead>
            <tbody>
              {data.map((request) => (
                <AccountRequestRow
                  key={request.id}
                  request={request}
                  onApproved={(response) => {
                    setApproval({ email: request.email, response });
                    setNotice(null);
                    remove(request.id);
                  }}
                  onRejected={() => {
                    setNotice(`The request from ${request.email} was rejected.`);
                    remove(request.id);
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
