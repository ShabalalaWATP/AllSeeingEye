import { useMemo, useState, type ReactNode } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { CATEGORIES } from '@/lib/api/eventSchemas';
import { fetchPlatformConnections, fetchSourceCatalogue } from '@/lib/api/sourceContext';
import { CATEGORY_STYLES } from '@/lib/categories';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { AttentionList } from './AttentionList';
import { CatalogueFilterBar } from './CatalogueFilterBar';
import { CatalogueSummary } from './CatalogueSummary';
import { PlatformConnections } from './PlatformConnections';
import { SourceAssetRow } from './SourceAssetRow';
import { SourceCatalogueRow } from './SourceCatalogueRow';
import { FAMILY_LABELS, catalogueEntries, type CatalogueEntry } from './catalogueEntries';
import { EMPTY_FILTERS, filterEntries, languageName, nationName } from './catalogueFilters';
import type { CatalogueFilters } from './catalogueFilters';

const ASSET_SECTIONS = [
  'camera_index',
  'map_layer',
  'ukraine_dataset',
  'reference_dataset',
] as const;

function Section({
  label,
  count,
  dot,
  children,
}: {
  label: string;
  count: number;
  dot?: string;
  children: ReactNode;
}) {
  return (
    <section aria-label={label}>
      <h3 className="flex items-center gap-3 border-b border-line py-3 text-lg font-semibold">
        {dot && (
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: dot }}
            aria-hidden="true"
          />
        )}
        {label}
        <span className="font-mono text-xs font-normal text-muted">{count}</span>
      </h3>
      <ul className="divide-y divide-line">{children}</ul>
    </section>
  );
}

export default function SourcesPage() {
  const { data, error, loading, reload } = useScopedResource(fetchSourceCatalogue);
  const platform = useScopedResource(fetchPlatformConnections);
  const [filters, setFilters] = useState<CatalogueFilters>(EMPTY_FILTERS);
  const change = (key: keyof CatalogueFilters, value: string) =>
    setFilters((old) => ({ ...old, [key]: value }));
  const sources = useMemo(() => data?.items ?? [], [data]);
  const entries = useMemo(() => catalogueEntries(sources, data?.assets ?? []), [sources, data]);
  const matches = useMemo(() => filterEntries(entries, filters), [entries, filters]);
  const nations = [...new Set(sources.flatMap((source) => source.coverage_countries))].sort(
    (a, b) => nationName(a).localeCompare(nationName(b)),
  );
  const regions = [...new Set(sources.flatMap((source) => source.coverage_regions))].sort();
  const languages = [...new Set(sources.map((source) => source.language))].sort((a, b) =>
    languageName(a).localeCompare(languageName(b)),
  );
  const topics = CATEGORIES.filter((topic) => sources.some((source) => source.category === topic));
  const filtered = Object.values(filters).some(Boolean);
  const focus = (next: Partial<CatalogueFilters>) => {
    setFilters({ ...EMPTY_FILTERS, ...next });
    document.getElementById('source-catalogue')?.scrollIntoView({ block: 'start' });
  };
  const matchingSources = matches.flatMap((entry: CatalogueEntry) =>
    entry.source ? [entry.source] : [],
  );
  return (
    <section
      className="h-full min-w-0 overflow-y-auto px-4 py-6 sm:px-7 lg:px-10"
      aria-label="Source catalogue"
    >
      <div className="mx-auto max-w-6xl space-y-8 pb-24">
        <header className="relative overflow-hidden rounded-2xl border border-line/70 bg-surface/50 px-5 py-6 sm:px-7">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_80%_at_100%_0%,color-mix(in_srgb,var(--color-ember)_12%,transparent),transparent_70%)]"
          />
          <div className="relative">
            <p className="mb-2 font-mono text-[10px] tracking-[0.22em] text-cyan uppercase">
              Collection directory
            </p>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Sources and connections
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">
              Every feed, research capability, camera provider, map layer and dataset this
              deployment uses, with what each one is doing right now. Values are never shown; a
              missing key names the server setting that unlocks it.
            </p>
          </div>
        </header>
        {loading && !data && <LoadingNote label="Loading source catalogue" />}
        {error !== null && (
          <Alert tone="error">
            {describeError(error)}{' '}
            <Button variant="secondary" onClick={() => void reload()}>
              Retry sources
            </Button>
          </Alert>
        )}
        {data && (
          <CatalogueSummary
            entries={entries}
            connection={filters.connection}
            family={filters.family}
            onConnection={(connection) => focus({ connection })}
            onFamily={(family) => focus({ family })}
          />
        )}
        {data && <AttentionList entries={entries} />}
        <PlatformConnections
          data={platform.data}
          loading={platform.loading}
          error={platform.error}
          onRetry={() => void platform.reload()}
        />
        <div id="source-catalogue" className="scroll-mt-4 space-y-4">
          <h2 className="text-lg font-semibold">Source catalogue</h2>
          <CatalogueFilterBar
            filters={filters}
            onChange={change}
            topics={topics}
            nations={nations}
            regions={regions}
            languages={languages}
          />
          {data && (
            <div className="flex items-center justify-between border-b border-line pb-3">
              <p role="status" className="text-sm text-muted">
                <span className="font-mono text-text">{matches.length}</span> of {entries.length}{' '}
                entries
              </p>
              {filtered && (
                <Button variant="secondary" onClick={() => setFilters(EMPTY_FILTERS)}>
                  Clear filters
                </Button>
              )}
            </div>
          )}
          {data && entries.length === 0 && (
            <p className="text-sm text-muted">No sources are registered.</p>
          )}
          {entries.length > 0 && matches.length === 0 && (
            <div className="py-10 text-center">
              <p className="text-sm text-muted">No sources match your search.</p>
              <p className="mt-2 text-xs text-muted">Try a broader search or clear the filters.</p>
            </div>
          )}
          <div className="space-y-8">
            {topics.map((topic) => {
              const rows = matchingSources.filter((source) => source.category === topic);
              if (!rows.length) return null;
              return (
                <Section
                  key={topic}
                  label={`${CATEGORY_STYLES[topic].label} sources`}
                  count={rows.length}
                  dot={CATEGORY_STYLES[topic].css}
                >
                  {rows.map((source) => (
                    <SourceCatalogueRow key={source.id} source={source} />
                  ))}
                </Section>
              );
            })}
            {ASSET_SECTIONS.map((family) => {
              const rows = matches.flatMap((entry) =>
                entry.asset?.family === family ? [entry.asset] : [],
              );
              if (!rows.length) return null;
              return (
                <Section key={family} label={FAMILY_LABELS[family]} count={rows.length}>
                  {rows.map((asset) => (
                    <SourceAssetRow key={asset.id} asset={asset} />
                  ))}
                </Section>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
