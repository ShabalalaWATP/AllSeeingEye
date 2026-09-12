import { AttributionControl } from 'maplibre-gl';
import type { Map as MapLibreMap } from 'maplibre-gl';
import { expect, it, vi } from 'vitest';
import { ATTRIBUTION_OPTIONS, collapseInitialAttribution } from './mapAttribution';
import { EOX_ATTRIBUTION, OS_ATTRIBUTION } from './baseLayers';

function nativeControl() {
  let attribution = EOX_ATTRIBUTION;
  const container = document.createElement('div');
  document.body.append(container);
  const handlers = new Map<string, (event: unknown) => void>();
  const map = {
    style: {
      stylesheet: {},
      tileManagers: {
        imagery: { used: true, getSource: () => ({ attribution }) },
        labels: {
          used: true,
          getSource: () => ({
            attribution: '<a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          }),
        },
      },
    },
    _getUIString: () => 'Toggle attribution',
    getCanvasContainer: () => container,
    on: (event: string, handler: (event: unknown) => void) => handlers.set(event, handler),
    off: vi.fn(),
  };
  const control = new AttributionControl(ATTRIBUTION_OPTIONS);
  const element = control.onAdd(map as unknown as MapLibreMap);
  container.append(element);
  return {
    container,
    control,
    details: element as HTMLDetailsElement,
    summary: element.querySelector('summary')!,
    replaceCredits: () => {
      attribution = OS_ATTRIBUTION;
      handlers.get('sourcedata')?.({ dataType: 'source', sourceDataType: 'metadata' });
    },
  };
}

it('closes native attribution initially while preserving its expandable provider credits', () => {
  const { container, control, details, summary } = nativeControl();
  expect(details.open).toBe(true);
  collapseInitialAttribution(container);
  expect(details.open).toBe(false);
  expect(details).not.toHaveClass('maplibregl-compact-show');
  expect(summary).toHaveAccessibleName('Toggle attribution');
  expect(details.querySelector('a[href="https://s2maps.eu"]')).not.toBeNull();
  expect(details.querySelector('a[href="https://www.openstreetmap.org/copyright"]')).not.toBeNull();
  expect(details.querySelector('a[href="https://maplibre.org/"]')).not.toBeNull();
  summary.click();
  expect(details.open).toBe(true);
  expect(details).toHaveClass('maplibregl-compact-show');
  summary.click();
  expect(details.open).toBe(false);
  expect(details).not.toHaveClass('maplibregl-compact-show');
  control.onRemove();
  container.remove();
});

it('updates source credits without overriding the user disclosure choice', () => {
  const { container, control, details, summary, replaceCredits } = nativeControl();
  collapseInitialAttribution(container);
  replaceCredits();
  expect(details.open).toBe(false);
  expect(details).toHaveTextContent(OS_ATTRIBUTION);
  expect(details).not.toHaveTextContent('Sentinel-2 cloudless');
  summary.click();
  expect(details.open).toBe(true);
  replaceCredits();
  expect(details.open).toBe(true);
  control.onRemove();
  container.remove();
});

it('allows a map with no attribution DOM, including lightweight test maps', () => {
  expect(() => collapseInitialAttribution(document.createElement('div'))).not.toThrow();
});
