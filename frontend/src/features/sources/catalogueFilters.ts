import type { CatalogueSource } from '@/lib/api/sourceContext';
import { CATEGORY_STYLES } from '@/lib/categories';

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
  topic: string;
  nation: string;
  language: string;
  access: string;
  mode: string;
}
export const EMPTY_FILTERS: CatalogueFilters = {
  query: '',
  topic: '',
  nation: '',
  language: '',
  access: '',
  mode: '',
};
export function filterSources(sources: readonly CatalogueSource[], filters: CatalogueFilters) {
  const terms = filters.query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
  return sources
    .filter((source) => {
      const text = [
        source.name,
        source.id,
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
      ]
        .join(' ')
        .toLocaleLowerCase();
      return (
        terms.every((term) => text.includes(term)) &&
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
        (!filters.access || source.requires_key === (filters.access === 'key')) &&
        (!filters.mode || source.collection_mode === filters.mode)
      );
    })
    .sort((a, b) => a.name.localeCompare(b.name, 'en-GB'));
}
