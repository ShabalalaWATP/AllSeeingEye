import { useCallback, useState } from 'react';

import { AdminIcon } from '@/components/admin/AdminIcon';
import { AdminPage, AdminSection, EmptyState } from '@/components/admin/AdminPage';
import { StatusPill } from '@/components/admin/StatusPill';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Table, Th } from '@/components/ui/Table';
import { listPendingAccountRequests } from '@/lib/api/admin';
import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';
import { useResource } from '@/lib/hooks/useResource';

import { AccountRequestRow } from './AccountRequestRow';
import { RevealedLinkList } from './RevealedLinkList';
import { useRevealedLinks } from './useRevealedLinks';

interface Notice {
  tone: 'success' | 'info';
  text: string;
}

export default function AdminRequestsPage() {
  const { data, error, loading, setData, reload } = useResource(listPendingAccountRequests);
  const revealed = useRevealedLinks();
  const [notice, setNotice] = useState<Notice | null>(null);

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
      <RevealedLinkList links={revealed.links} dismiss={revealed.dismiss} />
      {notice === null ? null : <Alert tone={notice.tone}>{notice.text}</Alert>}
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
                    if (response.activation_link === null) {
                      setNotice({
                        tone: 'success',
                        text: `${request.email} approved. The activation email has been sent and expires ${formatUtc(response.expires_at)}.`,
                      });
                    } else {
                      setNotice(null);
                      revealed.reveal({
                        title: `Activation link for ${request.email}`,
                        link: response.activation_link,
                        expiresAt: response.expires_at,
                      });
                    }
                    remove(request.id);
                  }}
                  onRejected={() => {
                    setNotice({
                      tone: 'info',
                      text: `The request from ${request.email} was rejected.`,
                    });
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
