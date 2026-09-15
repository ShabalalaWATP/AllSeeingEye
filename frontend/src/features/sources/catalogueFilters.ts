import type { CatalogueSource } from '@/lib/api/sourceContext';
import { CATEGORY_STYLES } from '@/lib/categories';
import { FAMILY_LABELS, type CatalogueEntry } from './catalogueEntries';
import { CONNECTION_META, connectionGroup } from './connectionPresentation';

const nations = new Intl.DisplayNames(['en-GB'], { type: 'region' });
const languages = new Intl.DisplayNames(['en-GB'], { type: 'language' });
export function nationName(code: string) {
  try {
    return nations.of(code) ?? code;
  } catch {
    return code;
  }
}
export function languageName(code: string) {
  try {
    return languages.of(code) ?? code;
  } catch {
    return code;
  }
}
export function coverageLabel(source: CatalogueSource) {
  if (source.coverage_scope === 'global') return 'Worldwide';
  const areas = [...source.coverage_countries.map(nationName), ...source.coverage_regions];
  return areas.length ? areas.join(' · ') : 'Coverage unspecified';
}
export interface CatalogueFilters {
  query: string;
  family: string;
  topic: string;
  nation: string;
  language: string;
  access: string;
  connection: string;
}
export const EMPTY_FILTERS: CatalogueFilters = {
  query: '',
  family: '',
  topic: '',
  nation: '',
  language: '',
  access: '',
  connection: '',
};

function sourceText(source: CatalogueSource) {
  return [
    source.organisation,
    source.parent_organisation,
    source.category,
    source.category === 'maritime' ? 'ships boats shipping AIS' : '',
    CATEGORY_STYLES[source.category].label,
    languageName(source.language),
    source.language,
    coverageLabel(source),
    source.coverage_note,
    ...source.coverage_countries,
  ];
}

function matchesSource(source: CatalogueSource, filters: CatalogueFilters) {
  return (
    (!filters.topic || source.category === filters.topic) &&
    (!filters.nation ||
      (filters.nation === 'global'
        ? source.coverage_scope === 'global'
        : filters.nation === 'unspecified'
          ? source.coverage_scope === 'unspecified'
          : filters.nation.startsWith('region:')
            ? source.coverage_regions.includes(filters.nation.slice(7))
            : source.coverage_countries.includes(filters.nation))) &&
    (!filters.language || source.language === filters.language) &&
    (!filters.access || source.requires_key === (filters.access === 'key'))
  );
}

/** Topic, country and language describe feeds and research only, so they exclude data assets. */
export function filterEntries(entries: readonly CatalogueEntry[], filters: CatalogueFilters) {
  const terms = filters.query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
  const sourceOnly = Boolean(filters.topic || filters.nation || filters.language);
  return entries
    .filter((entry) => {
      const { source, asset } = entry;
      const text = [
        entry.name,
        entry.id,
        FAMILY_LABELS[entry.family],
        CONNECTION_META[entry.state].label,
        entry.requirement?.setting ?? '',
        ...(source ? sourceText(source) : []),
        ...(asset ? [asset.organisation, asset.description, asset.coverage_note] : []),
      ]
        .join(' ')
        .toLocaleLowerCase();
      const keyed =
        entry.requirement?.kind === 'api_key' || entry.requirement?.kind === 'credentials';
      return (
        terms.every((term) => text.includes(term)) &&
        (!filters.family || entry.family === filters.family) &&
        (!filters.connection || connectionGroup(entry.state) === filters.connection) &&
        (source
          ? matchesSource(source, filters)
          : !sourceOnly && (!filters.access || keyed === (filters.access === 'key')))
      );
    })
    .sort((a, b) => a.name.localeCompare(b.name, 'en-GB'));
}
