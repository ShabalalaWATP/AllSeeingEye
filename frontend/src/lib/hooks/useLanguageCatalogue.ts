import { fetchLanguageCatalogue } from '@/lib/api/languages';
import { useResource } from './useResource';

/** Capability metadata is shared across users and contains no personal settings. */
export function useLanguageCatalogue() {
  return useResource(fetchLanguageCatalogue);
}
