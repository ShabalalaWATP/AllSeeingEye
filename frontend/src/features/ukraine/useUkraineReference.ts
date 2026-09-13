import { useCallback } from 'react';

import { fetchUkraineReference, type UkraineReference } from '@/lib/api/ukraine';
import { useResource } from '@/lib/hooks/useResource';

/** Loads the curated reference notes once; they change only when the operator re-imports. */
export function useUkraineReference(load: () => Promise<UkraineReference> = fetchUkraineReference) {
  const loader = useCallback(() => load(), [load]);
  return useResource<UkraineReference>(loader);
}
