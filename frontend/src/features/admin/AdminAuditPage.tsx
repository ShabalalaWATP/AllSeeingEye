import { AdminPage, AdminSection, EmptyState } from '@/components/admin/AdminPage';
import { StatusPill } from '@/components/admin/StatusPill';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Table, Td, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';

import { describeAction } from './overview/overviewSummaries';
import { useAuditLog } from './useAuditLog';

const DETAILS_LIMIT = 120;

/** Details are shown as plain JSON text, never rendered as markup. */
export function summariseDetails(details: Record<string, unknown>): string {
  const text = JSON.stringify(details);
  if (text === '{}') return '';
  return text.length > DETAILS_LIMIT ? `${text.slice(0, DETAILS_LIMIT - 3)}...` : text;
}

export default function AdminAuditPage() {
  const { entries, nextBefore, loading, error, loadMore } = useAuditLog();

  return (
    <AdminPage
      eyebrow="Oversight and security"
      title="Audit log"
      description="Recorded administrative and authentication actions, newest first. Entries are read only and details are shown as plain text."
      meta={
        entries.length === 0 ? undefined : (
          <StatusPill tone="info" icon="audit">
            {entries.length} {entries.length === 1 ? 'entry' : 'entries'} loaded
            {nextBefore === null ? '' : ', more available'}
          </StatusPill>
        )
      }
    >
      {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
      <AdminSection title="Recorded actions" icon="audit">
        {entries.length === 0 && !loading ? (
          <EmptyState icon="audit" title="No audit entries yet.">
            Administrative actions such as approvals, role changes and connection updates are
            recorded here.
          </EmptyState>
        ) : (
          <Table caption="Audit log entries, newest first" stickyHeader>
            <thead>
              <tr>
                <Th>When</Th>
                <Th>Action</Th>
                <Th>Actor</Th>
                <Th>Subject</Th>
                <Th>IP</Th>
                <Th>Details</Th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} className="hover:bg-surface-2/50">
                  <Td className="py-2.5 font-mono text-xs whitespace-nowrap text-muted">
                    {formatUtc(entry.at)}
                  </Td>
                  <Td className="min-w-48 py-2.5">
                    <span className="block text-sm">{describeAction(entry.action)}</span>
                    <span className="block font-mono text-[11px] text-muted">{entry.action}</span>
                  </Td>
                  <Td className="py-2.5 font-mono text-xs">
                    {entry.actor_user_id === null ? (
                      <StatusPill tone="neutral">system</StatusPill>
                    ) : (
                      <span className="block max-w-32 truncate" title={entry.actor_user_id}>
                        {entry.actor_user_id}
                      </span>
                    )}
                  </Td>
                  <Td className="py-2.5">{entry.subject ?? ''}</Td>
                  <Td className="py-2.5 font-mono text-xs">{entry.ip ?? ''}</Td>
                  <Td className="min-w-48 py-2.5 font-mono text-xs break-all text-muted">
                    {summariseDetails(entry.details)}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
        {loading ? (
          <div className="mt-3">
            <LoadingNote label="Loading audit entries" />
          </div>
        ) : null}
        {nextBefore === null ? null : (
          <div className="mt-4 flex justify-center">
            <Button variant="secondary" busy={loading} onClick={loadMore}>
              Load more
            </Button>
          </div>
        )}
      </AdminSection>
    </AdminPage>
  );
}
