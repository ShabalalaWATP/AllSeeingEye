import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Table, Td, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';

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
    <section className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <h1 className="text-xl font-semibold">Audit log</h1>
      {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
      {entries.length === 0 && !loading ? (
        <p className="text-sm text-muted">No audit entries yet.</p>
      ) : (
        <Table caption="Audit log entries, newest first">
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
              <tr key={entry.id}>
                <Td className="font-mono text-xs whitespace-nowrap">{formatUtc(entry.at)}</Td>
                <Td className="font-mono text-xs">{entry.action}</Td>
                <Td className="font-mono text-xs">{entry.actor_user_id ?? 'system'}</Td>
                <Td>{entry.subject ?? ''}</Td>
                <Td className="font-mono text-xs">{entry.ip ?? ''}</Td>
                <Td className="font-mono text-xs break-all">{summariseDetails(entry.details)}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      {loading ? <LoadingNote label="Loading audit entries" /> : null}
      {nextBefore === null ? null : (
        <div>
          <Button variant="secondary" busy={loading} onClick={loadMore}>
            Load more
          </Button>
        </div>
      )}
    </section>
  );
}
