/** Validation at the shared map boundary; canonical evidence geometry is never changed here. */
import type { FitBoundsOptions, MapBounds, MapCamera } from './MapEngine';

/** Explicitly match the installed renderer defaults and keep restore validation in sync. */
export const CAMERA_MAX_ZOOM = 22;
export const CAMERA_MAX_PITCH = 60;
/** A generous UI inset cap; fitting is not a channel for arbitrary renderer dimensions. */
export const MAX_FIT_PADDING = 4096;

function bounded(value: number, min: number, max: number, field: string): number {
  if (!Number.isFinite(value) || value < min || value > max) {
    throw new RangeError(`Invalid map ${field}.`);
  }
  return value;
}

function wrap(value: number): number {
  bounded(value, -Number.MAX_VALUE, Number.MAX_VALUE, 'angle');
  return (((value % 360) + 540) % 360) - 180;
}

export function normaliseCamera(camera: MapCamera): MapCamera {
  return {
    center: [wrap(camera.center[0]), bounded(camera.center[1], -90, 90, 'latitude')],
    zoom: bounded(camera.zoom, 0, CAMERA_MAX_ZOOM, 'zoom'),
    bearing: wrap(camera.bearing),
    pitch: bounded(camera.pitch, 0, CAMERA_MAX_PITCH, 'pitch'),
  };
}

export function validateBounds(bounds: MapBounds): MapBounds {
  const west = bounded(bounds.west, -180, 180, 'west');
  const east = bounded(bounds.east, -180, 180, 'east');
  const south = bounded(bounds.south, -90, 90, 'south');
  const north = bounded(bounds.north, south, 90, 'north');
  return { west, south, east, north };
}

/** MapLibre may report continuous longitudes outside the canonical world copy. */
export function normaliseViewport(bounds: MapBounds): MapBounds {
  bounded(bounds.west, -Number.MAX_VALUE, Number.MAX_VALUE, 'west');
  bounded(bounds.east, bounds.west, Number.MAX_VALUE, 'east');
  const fullWorld = bounds.east - bounds.west >= 360;
  return validateBounds({
    ...bounds,
    west: fullWorld ? -180 : wrap(bounds.west),
    east: fullWorld ? 180 : wrap(bounds.east),
  });
}

export function validateFitOptions(options: FitBoundsOptions): Required<FitBoundsOptions> {
  return {
    padding: bounded(options.padding ?? 24, 0, MAX_FIT_PADDING, 'padding'),
    maxZoom: bounded(options.maxZoom ?? 16, 0, CAMERA_MAX_ZOOM, 'maximum zoom'),
  };
}
