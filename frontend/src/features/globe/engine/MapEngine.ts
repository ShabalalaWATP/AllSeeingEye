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

/** Data layers are opaque to the engine interface; the registry decides their shape. */
export type DataLayer = object;

export interface MapEngine {
  mount(container: HTMLElement): void;
  setProjection(projection: Projection): void;
  flyTo(target: FlyToTarget): void;
  /** Replaces the data layers drawn over the base map. */
  setLayers(layers: readonly DataLayer[]): void;
  /** Subscribes to an engine event and returns the unsubscribe function. */
  on(event: MapEngineEvent, handler: MapEngineHandler): () => void;
  destroy(): void;
}

export type MapEngineFactory = () => MapEngine;
