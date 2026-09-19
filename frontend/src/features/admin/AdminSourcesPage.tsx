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
import { summariseSources } from './overview/overviewSummaries';

/** Scheduled delivery health is separate from query-only source capabilities. */
export function summarise(sources: readonly Source[]): string {
  const summary = summariseSources(sources);
  const parts = (
    [
      [summary.healthy, 'healthy'],
      [summary.failing, 'failing'],
      [summary.blockedUpstream, 'blocked upstream'],
      [summary.idle, 'waiting'],
      [summary.switchedOff, 'switched off'],
      [summary.blockedByOperator, 'blocked by operator'],
      [summary.onDemand, 'on-demand'],
    ] as const
  )
    .filter(([count]) => count > 0)
    .map(([count, label]) => `${count} ${label}`);
  return `${sources.length} ${sources.length === 1 ? 'source' : 'sources'}${parts.length > 0 ? `: ${parts.join(', ')}` : ''}`;
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
        description="Health reflects scheduled feed polls. On-demand sources have no polling health; check the catalogue for requirements and availability. Disabling a source stops future collection; existing evidence stays available."
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
