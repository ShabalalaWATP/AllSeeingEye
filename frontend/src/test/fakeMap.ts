/** Stand-in for maplibre-gl's Map class: records constructor options and calls. */
import { vi } from 'vitest';

type Handler = (payload: unknown) => void;

export class FakeMap {
  static instances: FakeMap[] = [];

  readonly options: Record<string, unknown>;
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
  readonly flyTo = vi.fn();
  readonly remove = vi.fn();

  constructor(options: Record<string, unknown>) {
    this.options = options;
    FakeMap.instances.push(this);
  }

  fire(event: string, payload: unknown = {}): void {
    for (const handler of this.handlers.get(event) ?? []) handler(payload);
  }

  static reset(): void {
    FakeMap.instances = [];
  }
}

export { FakeMap as Map };
