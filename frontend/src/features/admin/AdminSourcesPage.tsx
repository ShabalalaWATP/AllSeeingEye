import { useCallback } from 'react';

import { AdminIcon } from '@/components/admin/AdminIcon';
import { AdminPage, AdminSection, EmptyState } from '@/components/admin/AdminPage';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Table, Th } from '@/components/ui/Table';
import { fetchSources } from '@/lib/api/events';
import type { Source, SourceHealth } from '@/lib/api/eventSchemas';
import { describeError } from '@/lib/api/errors';
import { useNow } from '@/lib/hooks/useNow';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

import { FirmsConnectionPanel } from './FirmsConnectionPanel';
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
  const { data, error, loading, setData, key, refresh } = useScopedResource(fetchSources);
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
    <AdminPage
      eyebrow="Research services"
      title="Sources"
      description="Control collection across live feeds and on-demand research. Connection tests fetch a bounded sample without publishing or saving records. Manage NASA FIRMS credentials below; other source credentials remain operator configured."
      meta={
        data === null ? undefined : (
          <p className="inline-flex items-center gap-2 text-xs text-muted">
            <AdminIcon name="sources" size={14} className="text-ember" />
            {summarise(data)}
          </p>
        )
      }
      actions={
        <Button variant="secondary" busy={loading} onClick={() => void refresh()}>
          <AdminIcon name="refresh" size={16} />
          Refresh
        </Button>
      }
    >
      <FirmsConnectionPanel key={key} />
      {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
      <AdminSection
        title="Collection registry"
        icon="sources"
        description="Health reflects the most recent polls. Disabling a source stops future collection; existing evidence stays available."
      >
        {data === null ? (
          loading ? (
            <LoadingNote label="Loading sources" />
          ) : null
        ) : data.length === 0 ? (
          <EmptyState icon="sources" title="No sources are registered." />
        ) : (
          <Table caption="Sources" stickyHeader>
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
                <SourceRow
                  key={`${key}:${item.id}`}
                  source={item}
                  now={now}
                  onReset={replaceHealth}
                  onActivation={(id, enabled) =>
                    setData(
                      (current) =>
                        current?.map((source) =>
                          source.id === id ? { ...source, enabled } : source,
                        ) ?? null,
                    )
                  }
                />
              ))}
            </tbody>
          </Table>
        )}
      </AdminSection>
    </AdminPage>
  );
}
