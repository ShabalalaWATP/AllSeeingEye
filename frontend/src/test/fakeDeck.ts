/** Stand-in for MapLibreOverlay: records the props it is given. */
import { vi } from 'vitest';

export class MapboxOverlay {
  static instances: MapboxOverlay[] = [];

  props: Record<string, unknown>;
  readonly canvas = document.createElement('canvas');
  readonly getCanvas = vi.fn(() => this.canvas);
  readonly finalize = vi.fn();
  readonly pickMultipleObjects = vi.fn<(options: unknown) => { object: unknown }[]>(() => []);
  readonly setProps = vi.fn((props: Record<string, unknown>) => {
    this.props = { ...this.props, ...props };
  });

  constructor(props: Record<string, unknown>) {
    this.props = props;
    MapboxOverlay.instances.push(this);
  }

  static reset(): void {
    MapboxOverlay.instances = [];
  }
}

export { MapboxOverlay as MapLibreOverlay };
