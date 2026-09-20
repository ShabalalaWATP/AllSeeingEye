/**
 * Base-map and renderer lifecycle shared by live and saved-report maps.
 * Data overlays deliberately use deck.gl layers across engine implementations.
 */
import type { Layer } from '@deck.gl/core';
import type { BaseLayer } from './baseLayers';

export type Projection = 'globe' | 'mercator';

export type MapEngineEvent = 'load' | 'move' | 'moveend' | 'click' | 'error';

export type MapEngineHandler = (payload: unknown) => void;

export interface CursorPosition {
  lon: number;
  lat: number;
}

export type CursorHandler = (position: CursorPosition) => void;
export type SketchMode = 'navigate' | 'points' | 'drag';
export interface SketchDrag {
  phase: 'start' | 'move' | 'end' | 'cancel';
  start: CursorPosition;
  current: CursorPosition;
}
export type SketchDragHandler = (event: SketchDrag) => void;

export interface FlyToTarget {
  /** [longitude, latitude] */
  center: [number, number];
  zoom: number;
}

/** Engine limits: zoom 0..22, pitch 0..60. Longitude and bearing are wrapped to [-180, 180). */
export interface MapCamera extends FlyToTarget {
  bearing: number;
  pitch: number;
}

/** WGS84 bounds. West > east denotes a box crossing the antimeridian. */
export interface MapBounds {
  west: number;
  south: number;
  east: number;
  north: number;
}

export interface FitBoundsOptions {
  /** Padding in CSS pixels, 0..4096, defaults to 24. */
  padding?: number;
  /** Maximum fitted zoom, defaults to 16. */
  maxZoom?: number;
}

/** The overlay renderer consumes deck.gl layers, including their loading lifecycle. */
export type DataLayer = Layer;

/** Capability used by selection controls that only move the camera. */
export interface MapFocus {
  flyTo(target: FlyToTarget): void;
}

export type MapRenderStatus = 'ready' | 'recovering' | 'failed';

export interface EngineOptions {
  /** Sanitised renderer lifecycle notices, never upstream data or credentials. */
  onRenderStatus?: (status: MapRenderStatus, message: string) => void;
  /** Dedicated, fixed-size export instances only. Preserves the base map drawing buffer. */
  captureEnabled?: boolean;
  /** Returns the session's access token for requests to our own API (tile proxy), or null. */
  authHeader?: () => string | null;
}

export interface MapEngine extends MapFocus {
  mount(container: HTMLElement): void;
  setProjection(projection: Projection): void;
  setBaseLayer(layer: BaseLayer): void;
  /** Lite mode drops the atmosphere and animated camera moves. */
  setLite(lite: boolean): void;
  /** Subscribes to cursor positions over the map and returns the unsubscribe function. */
  onCursor(handler: CursorHandler): () => void;
  onDrag?(handler: SketchDragHandler): () => void;
  setSketchMode?(mode: SketchMode): void;
  /** Slowly turns the globe while enabled (the ops-room idle motion); off stops the camera. */
  spin(enabled: boolean): void;
  /** The camera's current zoom level, 0 when nothing is mounted. */
  getZoom(): number;
  pickObjectsAt?(x: number, y: number): readonly unknown[];
  /** Null before mount or after destruction; returns an independent camera snapshot. */
  getCamera(): MapCamera | null;
  /** Immediate, stops idle spin; invalid values throw RangeError, unmounted calls do nothing. */
  restoreCamera(camera: MapCamera): void;
  /** Geographic viewport envelope, not an AOI or exact visible footprint. Null when unmounted. */
  getViewportBounds(): MapBounds | null;
  /** Immediate fit; renderer projection constraints may limit polar views. Does not edit geometry. */
  fitBounds(bounds: MapBounds, options?: FitBoundsOptions): void;
  /** Replaces the data layers drawn over the base map. */
  setLayers(layers: readonly DataLayer[]): void;
  /** Subscribes to an engine event and returns the unsubscribe function. */
  on(event: MapEngineEvent, handler: MapEngineHandler): () => void;
  /** Captures actual base-map and data canvases on a dedicated export instance. */
  captureImage(signal: AbortSignal): Promise<Blob>;
  destroy(): void;
}

export type MapEngineFactory = (options?: EngineOptions) => MapEngine;
