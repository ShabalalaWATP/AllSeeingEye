import type {
  AssetFamily,
  CatalogueSource,
  ConnectionState,
  SourceAsset,
  SourceRequirement,
} from '@/lib/api/sourceContext';
import {
  GROUPS,
  actionRank,
  connectionGroup,
  isActionable,
  type ConnectionGroup,
} from './connectionPresentation';

export type Family = 'feed' | 'research' | AssetFamily;

export const FAMILIES: readonly Family[] = [
  'feed',
  'research',
  'camera_index',
  'map_layer',
  'ukraine_dataset',
  'reference_dataset',
];

export const FAMILY_LABELS: Record<Family, string> = {
  feed: 'Scheduled feeds',
  research: 'On-demand research',
  camera_index: 'Camera indexes',
  map_layer: 'Map layers and services',
  ukraine_dataset: 'Ukraine tracker datasets',
  reference_dataset: 'Reference datasets',
};

/** A feed, research capability or data asset, reduced to what totals and attention need. */
export interface CatalogueEntry {
  id: string;
  name: string;
  family: Family;
  state: ConnectionState;
  requirement: SourceRequirement | null;
  detail: string;
  source?: CatalogueSource;
  asset?: SourceAsset;
}

export function catalogueEntries(
  sources: readonly CatalogueSource[],
  assets: readonly SourceAsset[],
): CatalogueEntry[] {
  return [
    ...sources.map((source): CatalogueEntry => ({
      id: source.id,
      name: source.name,
      family: source.collection_mode === 'on_demand' ? 'research' : 'feed',
      state: source.connection.state,
      requirement: source.connection.requirement,
      detail: source.connection.detail,
      source,
    })),
    ...assets.map((asset): CatalogueEntry => ({
      id: asset.id,
      name: asset.name,
      family: asset.family,
      state: asset.state,
      requirement: asset.requirement,
      detail: asset.detail,
      asset,
    })),
  ];
}

export function summariseGroups(entries: readonly CatalogueEntry[]) {
  const totals = Object.fromEntries(GROUPS.map((group) => [group, 0])) as Record<
    ConnectionGroup,
    number
  >;
  for (const entry of entries) totals[connectionGroup(entry.state)] += 1;
  return totals;
}

export function summariseFamilies(entries: readonly CatalogueEntry[]) {
  const totals = Object.fromEntries(FAMILIES.map((family) => [family, 0])) as Record<
    Family,
    number
  >;
  for (const entry of entries) totals[entry.family] += 1;
  return totals;
}

/** Actionable entries, refusals first, then paused feeds, then missing settings. */
export function attentionEntries(entries: readonly CatalogueEntry[]) {
  return entries
    .filter((entry) => isActionable(entry.state, entry.requirement))
    .sort(
      (a, b) => actionRank(a.state) - actionRank(b.state) || a.name.localeCompare(b.name, 'en-GB'),
    );
}

/** The sentence that explains why an entry needs attention. */
export function attentionReason(entry: CatalogueEntry) {
  if (entry.state === 'blocked_upstream' || entry.state === 'failing') return entry.detail;
  return entry.requirement?.note ?? entry.detail;
}
