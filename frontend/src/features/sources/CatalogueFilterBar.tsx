import type { ReactNode } from 'react';
import type { Category } from '@/lib/api/eventSchemas';
import { CATEGORY_STYLES } from '@/lib/categories';
import { FAMILIES, FAMILY_LABELS } from './catalogueEntries';
import { languageName, nationName, type CatalogueFilters } from './catalogueFilters';
import { GROUPS, GROUP_LABELS } from './connectionPresentation';

export const inputClass =
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

export function CatalogueFilterBar({
  filters,
  onChange,
  topics,
  nations,
  regions,
  languages,
}: {
  filters: CatalogueFilters;
  onChange: (key: keyof CatalogueFilters, value: string) => void;
  topics: readonly Category[];
  nations: readonly string[];
  regions: readonly string[];
  languages: readonly string[];
}) {
  return (
    <div className="space-y-4" role="search" aria-label="Filter source catalogue">
      <label className="flex flex-col gap-2 text-xs text-muted">
        Search sources
        <input
          type="search"
          placeholder="Try news, Ukraine, cameras, an organisation or a setting name…"
          value={filters.query}
          onChange={(event) => onChange('query', event.target.value)}
          className={inputClass}
        />
      </label>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        <Filter label="Family" value={filters.family} onChange={(v) => onChange('family', v)}>
          <option value="">All families</option>
          {FAMILIES.map((family) => (
            <option key={family} value={family}>
              {FAMILY_LABELS[family]}
            </option>
          ))}
        </Filter>
        <Filter
          label="Connection"
          value={filters.connection}
          onChange={(v) => onChange('connection', v)}
        >
          <option value="">Any state</option>
          {GROUPS.map((group) => (
            <option key={group} value={group}>
              {GROUP_LABELS[group]}
            </option>
          ))}
        </Filter>
        <Filter label="Topic" value={filters.topic} onChange={(v) => onChange('topic', v)}>
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
          onChange={(v) => onChange('nation', v)}
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
        <Filter label="Language" value={filters.language} onChange={(v) => onChange('language', v)}>
          <option value="">All languages</option>
          {languages.map((code) => (
            <option key={code} value={code}>
              {languageName(code)}
            </option>
          ))}
        </Filter>
        <Filter label="Access" value={filters.access} onChange={(v) => onChange('access', v)}>
          <option value="">All access types</option>
          <option value="open">No API key required</option>
          <option value="key">API key required</option>
        </Filter>
      </div>
      <p className="text-xs leading-relaxed text-muted">
        Topic, country and language describe feeds and research, so choosing one hides camera, map,
        Ukraine and reference data. Countries describe declared coverage or research focus, not
        publisher nationality. States describe delivery on this server, not reliability.
      </p>
    </div>
  );
}
