/**
 * The seam between the globe page and the map library. Everything the page
 * needs goes through this interface so the library can be swapped in one folder.
 */
export type Projection = 'globe' | 'mercator';

export type MapEngineEvent = 'load' | 'move' | 'click' | 'error';

export type MapEngineHandler = (payload: unknown) => void;

export interface FlyToTarget {
  /** [longitude, latitude] */
  center: [number, number];
  zoom: number;
}

export interface MapEngine {
  mount(container: HTMLElement): void;
  setProjection(projection: Projection): void;
  flyTo(target: FlyToTarget): void;
  /** Subscribes to an engine event and returns the unsubscribe function. */
  on(event: MapEngineEvent, handler: MapEngineHandler): () => void;
  destroy(): void;
}

export type MapEngineFactory = () => MapEngine;
