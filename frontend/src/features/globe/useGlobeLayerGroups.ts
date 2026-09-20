import { useMemo } from 'react';
import type { Layer } from '@deck.gl/core';

export type GlobeLayerGroups = readonly (readonly Layer[] | 'events')[];
type Catalogues = Record<
  | 'grid'
  | 'infrastructure'
  | 'regions'
  | 'cameras'
  | 'figures'
  | 'context'
  | 'cyber'
  | 'radar'
  | 'network'
  | 'news'
  | 'tools',
  readonly Layer[]
>;

/** Draw order for dashboard catalogues; explicit data hooks remain in the page. */
export function useGlobeLayerGroups({
  grid,
  infrastructure,
  regions,
  cameras,
  figures,
  context,
  cyber,
  radar,
  network,
  news,
  tools,
}: Catalogues): GlobeLayerGroups {
  return useMemo<GlobeLayerGroups>(
    () => [
      grid,
      infrastructure,
      'events',
      regions,
      cameras,
      figures,
      context,
      cyber,
      radar,
      network,
      news,
      tools,
    ],
    [grid, infrastructure, regions, cameras, figures, context, cyber, radar, network, news, tools],
  );
}
