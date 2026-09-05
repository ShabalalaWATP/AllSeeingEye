/** Stand-in for @deck.gl/mapbox's MapboxOverlay: records the props it is given. */
import { vi } from 'vitest';

export class MapboxOverlay {
  static instances: MapboxOverlay[] = [];

  props: Record<string, unknown>;
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
