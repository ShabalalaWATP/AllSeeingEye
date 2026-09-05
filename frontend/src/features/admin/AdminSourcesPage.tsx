import { useCallback } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Table, Th } from '@/components/ui/Table';
import { fetchSources } from '@/lib/api/events';
import type { Source, SourceHealth } from '@/lib/api/eventSchemas';
import { describeError } from '@/lib/api/errors';
import { useNow } from '@/lib/hooks/useNow';
import { useResource } from '@/lib/hooks/useResource';

import { SourceRow } from './SourceRow';

/** "29 sources: 27 healthy, 1 degraded, 1 idle" without the zero counts. */
export function summarise(sources: readonly Source[]): string {
  const counts = new Map<SourceHealth['status'], number>();
  for (const item of sources)
    counts.set(item.health.status, (counts.get(item.health.status) ?? 0) + 1);
  const parts = (['healthy', 'degraded', 'idle', 'disabled'] as const)
    .filter((status) => (counts.get(status) ?? 0) > 0)
    .map((status) => `${counts.get(status)} ${status}`);
  return `${sources.length} sources${parts.length > 0 ? `: ${parts.join(', ')}` : ''}`;
}

export default function AdminSourcesPage() {
  const { data, error, loading, setData } = useResource(fetchSources);
  const now = useNow();

  const replaceHealth = useCallback(
    (health: SourceHealth) => {
      setData((current) =>
        current === null
          ? current
          : current.map((item) => (item.id === health.source_id ? { ...item, health } : item)),
      );
    },
    [setData],
  );

  return (
    <section className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <div className="flex items-baseline justify-between gap-4">
        <h1 className="text-xl font-semibold">Sources</h1>
        {data !== null && <p className="text-sm text-muted">{summarise(data)}</p>}
      </div>
      {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
      {data === null ? (
        loading ? (
          <LoadingNote label="Loading sources" />
        ) : null
      ) : (
        <Table caption="Sources">
          <thead>
            <tr>
              <Th>Source</Th>
              <Th>Category</Th>
              <Th>Grade</Th>
              <Th>Poll</Th>
              <Th>Status</Th>
              <Th>Last poll</Th>
              <Th>Last error</Th>
              <Th>Actions</Th>
            </tr>
          </thead>
          <tbody>
            {data.map((item) => (
              <SourceRow key={item.id} source={item} now={now} onReset={replaceHealth} />
            ))}
          </tbody>
        </Table>
      )}
    </section>
  );
}
