import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { fetchSourceCatalogue } from '@/lib/api/sourceContext';
import { CATEGORY_STYLES } from '@/lib/categories';
import { CATEGORIES } from '@/lib/api/eventSchemas';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { EMPTY_FILTERS, filterSources, languageName, nationName } from './catalogueFilters';
import type { CatalogueFilters } from './catalogueFilters';
import { SourceCatalogueRow } from './SourceCatalogueRow';

const inputClass =
  'min-h-11 w-full rounded-md border border-line bg-surface px-3 text-sm text-text focus-visible:outline-2 focus-visible:outline-ember';
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
  const [filters, setFilters] = useState<CatalogueFilters>(EMPTY_FILTERS);
  const change = (key: keyof CatalogueFilters, value: string) =>
    setFilters((old) => ({ ...old, [key]: value }));
  const matches = useMemo(() => filterSources(data ?? [], filters), [data, filters]);
  const nations = [...new Set(data?.flatMap((source) => source.coverage_countries) ?? [])].sort(
    (a, b) => nationName(a).localeCompare(nationName(b)),
  );
  const regions = [...new Set(data?.flatMap((source) => source.coverage_regions) ?? [])].sort();
  const languages = [...new Set(data?.map((source) => source.language) ?? [])].sort((a, b) =>
    languageName(a).localeCompare(languageName(b)),
  );
  const topics = CATEGORIES.filter((topic) => data?.some((source) => source.category === topic));
  const filtered = Object.values(filters).some(Boolean);
  return (
    <section
      className="h-full min-w-0 overflow-y-auto p-4 sm:p-6 lg:p-8"
      aria-label="Source catalogue"
    >
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="space-y-3 border-b border-line pb-6">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-cyan">
            Collection directory
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">Source catalogue</h1>
          <p className="max-w-2xl text-sm leading-relaxed text-muted">
            Find sources by topic, country coverage and language. Browse scheduled feeds and
            on-demand research tools in one place.
          </p>
        </header>
        <div className="space-y-4" role="search" aria-label="Filter source catalogue">
          <label className="flex flex-col gap-2 text-xs text-muted">
            Search sources
            <input
              type="search"
              placeholder="Try news, Ukraine, shipping or an organisation…"
              value={filters.query}
              onChange={(event) => change('query', event.target.value)}
              className={inputClass}
            />
          </label>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
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
            Worldwide sources are listed separately. An entry does not mean the source was queried
            or is currently connected.
          </p>
        </div>
        {loading && <LoadingNote label="Loading source catalogue" />}
        {error !== null && (
          <Alert tone="error">
            {describeError(error)}{' '}
            <Button variant="secondary" onClick={() => void reload()}>
              Retry sources
            </Button>
          </Alert>
        )}
        {data && (
          <div className="flex items-center justify-between border-b border-line pb-3">
            <p role="status" className="text-sm text-muted">
              <span className="font-mono text-text">{matches.length}</span> of {data.length} sources
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
                <h2 className="flex items-center gap-3 border-b border-line py-3 text-lg font-semibold">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: CATEGORY_STYLES[topic].css }}
                    aria-hidden="true"
                  />
                  {CATEGORY_STYLES[topic].label}
                  <span className="font-mono text-xs font-normal text-muted">{sources.length}</span>
                </h2>
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
    </section>
  );
}
