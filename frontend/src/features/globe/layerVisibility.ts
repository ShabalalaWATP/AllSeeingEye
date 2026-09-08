import type { Category } from '@/lib/api/eventSchemas';
import type { ObservationKind, ObservationVisibility } from './ObservationControls';

const PARENTS: Record<ObservationKind, Category> = {
  aircraft: 'aviation',
  vessels: 'maritime',
  firms: 'disaster',
};

/** A remembered subgroup preference is only visible while its parent is shown. */
export function isObservationShown(
  kind: ObservationKind,
  visibility: ObservationVisibility,
  hidden: readonly Category[],
): boolean {
  return visibility[kind] && !hidden.includes(PARENTS[kind]);
}

/** Enabling a hidden subgroup also restores its parent without flipping a saved on preference. */
export function toggleObservationLayer(
  kind: ObservationKind,
  visibility: ObservationVisibility,
  hidden: readonly Category[],
  onToggleObservation: (kind: ObservationKind) => void,
  onToggleCategory: (category: Category) => void,
): void {
  if (hidden.includes(PARENTS[kind])) {
    onToggleCategory(PARENTS[kind]);
    if (!visibility[kind]) onToggleObservation(kind);
  } else {
    onToggleObservation(kind);
  }
}
