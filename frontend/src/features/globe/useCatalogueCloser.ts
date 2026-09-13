import { useCallback } from 'react';

interface CatalogueClosers {
  radar: () => void;
  network: () => void;
  cameras: () => void;
  figures: () => void;
  infrastructure: () => void;
  regions: () => void;
  context: () => void;
  cyber: () => void;
  news: () => void;
}

/** Clear all catalogue selections before opening a different map feature. */
export function useCatalogueCloser(closers: CatalogueClosers) {
  const { radar, network, cameras, figures, infrastructure, regions, context, cyber, news } =
    closers;
  return useCallback(() => {
    radar();
    network();
    cameras();
    figures();
    infrastructure();
    regions();
    context();
    cyber();
    news();
  }, [radar, network, cameras, figures, infrastructure, regions, context, cyber, news]);
}
