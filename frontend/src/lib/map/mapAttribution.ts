import type { AttributionControlOptions } from 'maplibre-gl';

/** Keep the native control's automatic source credits and its MapLibre acknowledgement. */
export const ATTRIBUTION_OPTIONS: AttributionControlOptions = {
  compact: true,
  customAttribution: '<a href="https://maplibre.org/" target="_blank">MapLibre</a>',
};

/** MapLibre 6 opens compact attribution initially. Close once, retaining its native toggle. */
export function collapseInitialAttribution(container: HTMLElement): void {
  const attribution = container.querySelector<HTMLDetailsElement>('details.maplibregl-ctrl-attrib');
  if (!attribution) return;
  // Keep compact mode even while initial source metadata loads. Later source
  // updates retain the user's chosen disclosure state and refresh all credits.
  attribution.classList.add('maplibregl-compact');
  attribution.classList.remove('maplibregl-compact-show');
  attribution.open = false;
}
