import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { fetchPlatformConnections, fetchSourceCatalogue } from '@/lib/api/sourceContext';
import { CATEGORY_STYLES } from '@/lib/categories';
import { CATEGORIES } from '@/lib/api/eventSchemas';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { ConnectionBadge } from './ConnectionBadge';
import { PlatformConnections } from './PlatformConnections';
import { SourceCatalogueRow } from './SourceCatalogueRow';
import { EMPTY_FILTERS, filterSources, languageName, nationName } from './catalogueFilters';
import type { CatalogueFilters } from './catalogueFilters';
import {
  GROUP_LABELS,
  attentionSources,
  summariseConnections,
  type ConnectionGroup,
} from './connectionPresentation';

const inputClass =
  'min-h-11 w-full rounded-md border border-line bg-surface px-3 text-sm text-text focus-visible:outline-2 focus-visible:outline-ember';
const GROUPS: readonly ConnectionGroup[] = [
  'collecting',
  'attention',
  'key_missing',
  'on_demand',
  'off',
];
const GROUP_TONE: Record<ConnectionGroup, string> = {
  collecting: 'text-good',
  attention: 'text-amber',
  key_missing: 'text-critical',
  on_demand: 'text-cyan',
  off: 'text-muted',
};

function Filter({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  return (
    <label className="flex min-w-0 flex-col gap-2 text-xs text-muted">
      {label}
      <select
        className={inputClass}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {children}
      </select>
    </label>
  );
}

export default function SourcesPage() {
  const { data, error, loading, reload } = useScopedResource(fetchSourceCatalogue);
  const platform = useScopedResource(fetchPlatformConnections);
  const [filters, setFilters] = useState<CatalogueFilters>(EMPTY_FILTERS);
  const change = (key: keyof CatalogueFilters, value: string) =>
    setFilters((old) => ({ ...old, [key]: value }));
  const matches = useMemo(() => filterSources(data ?? [], filters), [data, filters]);
  // Totals describe the catalogue the tiles filter; platform services are listed separately.
  const totals = useMemo(() => summariseConnections(data ?? []), [data]);
  const attention = useMemo(() => attentionSources(data ?? []), [data]);
  const nations = [...new Set(data?.flatMap((source) => source.coverage_countries) ?? [])].sort(
    (a, b) => nationName(a).localeCompare(nationName(b)),
  );
  const regions = [...new Set(data?.flatMap((source) => source.coverage_regions) ?? [])].sort();
  const languages = [...new Set(data?.map((source) => source.language) ?? [])].sort((a, b) =>
    languageName(a).localeCompare(languageName(b)),
  );
  const topics = CATEGORIES.filter((topic) => data?.some((source) => source.category === topic));
  const filtered = Object.values(filters).some(Boolean);
  const focusGroup = (group: ConnectionGroup) => {
    setFilters({ ...EMPTY_FILTERS, connection: group });
    document.getElementById('source-catalogue')?.scrollIntoView({ block: 'start' });
  };
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
              Every feed and research capability this deployment knows about, including keyed
              services that are waiting for a credential, with what each one is doing right now.
              Values are never shown; a missing key names the server setting that unlocks it.
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
          <ul aria-label="Connection totals" className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {GROUPS.map((group) => (
              <li key={group}>
                <button
                  type="button"
                  onClick={() => focusGroup(group)}
                  aria-pressed={filters.connection === group}
                  className={`flex w-full flex-col rounded-xl border p-4 text-left transition-colors hover:border-line ${filters.connection === group ? 'border-ember bg-surface-2' : 'border-line/70 bg-surface/60'}`}
                >
                  <span className="text-[11px] text-muted">{GROUP_LABELS[group]}</span>
                  <span
                    className={`mt-1 text-2xl font-semibold tracking-tight ${GROUP_TONE[group]}`}
                  >
                    {totals[group]}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {data && attention.length > 0 && (
          <section
            aria-label="Sources needing attention"
            className="rounded-xl border border-amber/40 bg-amber/5 p-4 sm:p-5"
          >
            <h2 className="text-sm font-semibold">Needs attention</h2>
            <p className="mt-1 text-xs leading-5 text-muted">
              Sources that cannot collect until a credential is added, a runtime is installed or
              repeated failures are reset by an administrator.
            </p>
            <ul className="mt-3 divide-y divide-line/60">
              {attention.slice(0, 12).map((source) => (
                <li key={source.id} className="flex flex-wrap items-center gap-3 py-2 text-sm">
                  <ConnectionBadge state={source.connection.state} />
                  <span className="font-medium">{source.name}</span>
                  <span className="min-w-0 flex-1 text-xs text-muted">
                    {source.connection.requirement?.note ?? source.connection.detail}
                  </span>
                  {source.connection.requirement?.setting && (
                    <span className="font-mono text-[10px] text-muted">
                      {source.connection.requirement.setting}
                    </span>
                  )}
                </li>
              ))}
            </ul>
            {attention.length > 12 && (
              <p className="mt-2 text-xs text-muted">
                {attention.length - 12} more in the catalogue below.
              </p>
            )}
          </section>
        )}
        <PlatformConnections
          data={platform.data}
          loading={platform.loading}
          error={platform.error}
          onRetry={() => void platform.reload()}
        />
        <div id="source-catalogue" className="scroll-mt-4 space-y-4">
          <h2 className="text-lg font-semibold">Source catalogue</h2>
          <div className="space-y-4" role="search" aria-label="Filter source catalogue">
            <label className="flex flex-col gap-2 text-xs text-muted">
              Search sources
              <input
                type="search"
                placeholder="Try news, Ukraine, shipping, an organisation or a setting name…"
                value={filters.query}
                onChange={(event) => change('query', event.target.value)}
                className={inputClass}
              />
            </label>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
              <Filter
                label="Connection"
                value={filters.connection}
                onChange={(value) => change('connection', value)}
              >
                <option value="">Any state</option>
                {GROUPS.map((group) => (
                  <option key={group} value={group}>
                    {GROUP_LABELS[group]}
                  </option>
                ))}
              </Filter>
              <Filter
                label="Topic"
                value={filters.topic}
                onChange={(value) => change('topic', value)}
              >
                <option value="">All topics</option>
                {topics.map((topic) => (
                  <option key={topic} value={topic}>
                    {CATEGORY_STYLES[topic].label}
                  </option>
                ))}
              </Filter>
              <Filter
                label="Country or region"
                value={filters.nation}
                onChange={(value) => change('nation', value)}
              >
                <option value="">All countries and regions</option>
                <option value="global">Worldwide</option>
                {nations.map((code) => (
                  <option key={code} value={code}>
                    {nationName(code)}
                  </option>
                ))}
                {regions.map((region) => (
                  <option key={region} value={`region:${region}`}>
                    {region}
                  </option>
                ))}
                <option value="unspecified">Coverage unspecified</option>
              </Filter>
              <Filter
                label="Language"
                value={filters.language}
                onChange={(value) => change('language', value)}
              >
                <option value="">All languages</option>
                {languages.map((code) => (
                  <option key={code} value={code}>
                    {languageName(code)}
                  </option>
                ))}
              </Filter>
              <Filter
                label="Collection"
                value={filters.mode}
                onChange={(value) => change('mode', value)}
              >
                <option value="">All collection methods</option>
                <option value="scheduled">Scheduled feeds</option>
                <option value="on_demand">On-demand research</option>
              </Filter>
              <Filter
                label="Access"
                value={filters.access}
                onChange={(value) => change('access', value)}
              >
                <option value="">All access types</option>
                <option value="open">No API key required</option>
                <option value="key">API key required</option>
              </Filter>
            </div>
            <p className="text-xs leading-relaxed text-muted">
              Countries describe declared coverage or research focus, not publisher nationality.
              Connection states describe delivery on this server, not editorial reliability.
            </p>
          </div>
          {data && (
            <div className="flex items-center justify-between border-b border-line pb-3">
              <p role="status" className="text-sm text-muted">
                <span className="font-mono text-text">{matches.length}</span> of {data.length}{' '}
                sources
              </p>
              {filtered && (
                <Button variant="secondary" onClick={() => setFilters(EMPTY_FILTERS)}>
                  Clear filters
                </Button>
              )}
            </div>
          )}
          {data?.length === 0 && <p className="text-sm text-muted">No sources are registered.</p>}
          {data && data.length > 0 && matches.length === 0 && (
            <div className="py-10 text-center">
              <p className="text-sm text-muted">No sources match your search.</p>
              <p className="mt-2 text-xs text-muted">Try a broader search or clear the filters.</p>
            </div>
          )}
          <div className="space-y-8">
            {topics.map((topic) => {
              const sources = matches.filter((source) => source.category === topic);
              if (!sources.length) return null;
              return (
                <section key={topic} aria-label={`${CATEGORY_STYLES[topic].label} sources`}>
                  <h3 className="flex items-center gap-3 border-b border-line py-3 text-lg font-semibold">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: CATEGORY_STYLES[topic].css }}
                      aria-hidden="true"
                    />
                    {CATEGORY_STYLES[topic].label}
                    <span className="font-mono text-xs font-normal text-muted">
                      {sources.length}
                    </span>
                  </h3>
                  <ul className="divide-y divide-line">
                    {sources.map((source) => (
                      <SourceCatalogueRow key={source.id} source={source} />
                    ))}
                  </ul>
                </section>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
