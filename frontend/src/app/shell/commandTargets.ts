/**
 * Everything the palette can jump to: workspace pages grouped as the rail groups
 * them, specialist trackers, map layers and tools, and, for an administrator, the
 * source catalogue by family. The rest of administration is absent on purpose; it
 * keeps its own guarded navigation, and the catalogue is offered only to the people
 * who can open it.
 */
import { FAMILIES, FAMILY_LABELS } from '@/features/sources/catalogueEntries';
import { catalogueHref } from '@/features/sources/catalogueFilters';
import { MAP_GUIDE_PANEL, mapLayerEntries, mapPanelHref } from '@/lib/mapLayerDirectory';
import { trackerModules, workspaceHome, workspaceSections } from '@/lib/workspaceNavigation';

export interface CommandTarget {
  readonly id: string;
  readonly label: string;
  readonly group: string;
  readonly description: string;
  readonly to: string;
}

export function commandTargets(options: { admin?: boolean } = {}): readonly CommandTarget[] {
  return [
    ...[{ title: 'Pages', items: [workspaceHome] }, ...workspaceSections].flatMap((section) =>
      section.items.map((page) => ({
        id: `page:${page.to}`,
        label: page.label,
        group: section.title,
        description: page.description,
        to: page.to,
      })),
    ),
    ...trackerModules.map((tracker) => ({
      id: `tracker:${tracker.to}`,
      label: tracker.label,
      group: 'Trackers',
      description: tracker.description,
      to: tracker.to,
    })),
    {
      id: 'map:guide',
      label: MAP_GUIDE_PANEL,
      group: 'Map',
      description: 'Every layer and tool the map offers, with what each one shows.',
      to: mapPanelHref(MAP_GUIDE_PANEL),
    },
    ...mapLayerEntries().map((entry) => ({
      id: `map:${entry.id}`,
      label: entry.label,
      group: 'Map',
      description: entry.description,
      to: entry.panel === undefined ? mapPanelHref(MAP_GUIDE_PANEL) : mapPanelHref(entry.panel),
    })),
    ...(options.admin
      ? FAMILIES.map((family) => ({
          id: `family:${family}`,
          label: FAMILY_LABELS[family],
          group: 'Sources',
          description: `Filter the source catalogue to ${FAMILY_LABELS[family].toLowerCase()}.`,
          to: catalogueHref({ family }),
        }))
      : []),
  ];
}

function rank(target: CommandTarget, terms: readonly string[]): number {
  const label = target.label.toLocaleLowerCase();
  const first = terms[0] ?? '';
  if (label.startsWith(first)) return 0;
  if (label.includes(first)) return 1;
  return 2;
}

/** Every term must appear somewhere; label matches come first, then catalogue order. */
export function matchTargets(
  targets: readonly CommandTarget[],
  query: string,
  limit = 40,
): readonly CommandTarget[] {
  const terms = query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
  if (terms.length === 0) return targets.slice(0, limit);
  return targets
    .map((target, order) => ({ target, order }))
    .filter(({ target }) => {
      const text = `${target.label} ${target.group} ${target.description}`.toLocaleLowerCase();
      return terms.every((term) => text.includes(term));
    })
    .sort((a, b) => rank(a.target, terms) - rank(b.target, terms) || a.order - b.order)
    .slice(0, limit)
    .map(({ target }) => target);
}
