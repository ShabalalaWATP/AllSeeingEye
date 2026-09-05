/** Stand-in for maplibre-gl's Map class: records constructor options and calls. */
import { vi } from 'vitest';

type Handler = (payload: unknown) => void;

interface StyleLayer {
  id: string;
  type: string;
}

/** The style layers the fake starts with: fills, one boundary line and one label layer. */
export const FAKE_STYLE_LAYERS: StyleLayer[] = [
  { id: 'background', type: 'background' },
  { id: 'water', type: 'fill' },
  { id: 'boundary_country_z0-4', type: 'line' },
  { id: 'place_city', type: 'symbol' },
];

export class FakeMap {
  static instances: FakeMap[] = [];

  readonly options: Record<string, unknown>;
  readonly layers: StyleLayer[] = FAKE_STYLE_LAYERS.map((layer) => ({ ...layer }));
  readonly sources = new Map<string, unknown>();
  private readonly handlers = new Map<string, Handler[]>();

  readonly on = vi.fn((event: string, handler: Handler) => {
    const list = this.handlers.get(event) ?? [];
    list.push(handler);
    this.handlers.set(event, list);
    return this;
  });
  readonly off = vi.fn((event: string, handler: Handler) => {
    const list = (this.handlers.get(event) ?? []).filter((item) => item !== handler);
    this.handlers.set(event, list);
    return this;
  });
  readonly setProjection = vi.fn();
  readonly setSky = vi.fn();
  readonly setPaintProperty = vi.fn();
  readonly flyTo = vi.fn();
  readonly jumpTo = vi.fn();
  readonly easeTo = vi.fn();
  readonly stop = vi.fn();
  getCenter(): { lng: number; lat: number } {
    return { lng: 10, lat: 30 };
  }
  readonly remove = vi.fn();
  readonly addControl = vi.fn();
  readonly removeControl = vi.fn();
  readonly setLayoutProperty = vi.fn();
  readonly addSource = vi.fn((id: string, spec: unknown) => {
    this.sources.set(id, spec);
  });
  readonly removeSource = vi.fn((id: string) => {
    this.sources.delete(id);
  });
  readonly getSource = vi.fn((id: string) => this.sources.get(id));
  readonly addLayer = vi.fn((layer: StyleLayer, before?: string) => {
    const index = before === undefined ? -1 : this.layers.findIndex((item) => item.id === before);
    if (index === -1) this.layers.push(layer);
    else this.layers.splice(index, 0, layer);
  });
  readonly removeLayer = vi.fn((id: string) => {
    const index = this.layers.findIndex((item) => item.id === id);
    if (index !== -1) this.layers.splice(index, 1);
  });
  readonly getStyle = vi.fn(() => ({ layers: this.layers }));
  /** Only the style's own layers plus anything added "exist"; unknown overrides are skipped. */
  readonly getLayer = vi.fn((id: string) => this.layers.find((layer) => layer.id === id));

  constructor(options: Record<string, unknown>) {
    this.options = options;
    FakeMap.instances.push(this);
  }

  getZoom(): number {
    return 1.5;
  }

  fire(event: string, payload: unknown = {}): void {
    for (const handler of this.handlers.get(event) ?? []) handler(payload);
  }

  static reset(): void {
    FakeMap.instances = [];
  }
}

export { FakeMap as Map };
