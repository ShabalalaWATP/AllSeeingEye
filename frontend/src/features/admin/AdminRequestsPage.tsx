import { useCallback, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
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
  const { data, error, loading, setData } = useResource(listPendingAccountRequests);
  const [approval, setApproval] = useState<Approval | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const remove = useCallback(
    (id: string) => {
      setData((current) => (current === null ? current : current.filter((item) => item.id !== id)));
    },
    [setData],
  );

  return (
    <section className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <h1 className="text-xl font-semibold">Account requests</h1>
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
      {data === null ? (
        loading ? (
          <LoadingNote label="Loading requests" />
        ) : null
      ) : data.length === 0 ? (
        <p className="text-sm text-muted">No pending requests.</p>
      ) : (
        <Table caption="Pending account requests">
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
    </section>
  );
}
