/**
 * Shared symbols for traffic, selected hazards and conflict report types.
 * Aircraft and vessels use their reported heading where available.
 */
import { IconLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import { sameLayerRows } from '@/lib/map/sameLayerRows';
import { SYMBOL_WINDING } from '@/lib/map/symbolWinding';

import type { LiveEvent } from '@/lib/api/eventSchemas';

import { CATEGORY_STYLES } from '@/lib/categories';
import { CYBER_SHIELD_MASK } from '@/lib/cyber';
import { NEWS_MASK } from '@/lib/newsSymbols';
import { conflictKind, type ConflictKind } from '@/lib/conflicts';
import { CONFLICT_ICON_SHAPES, CONFLICT_SYMBOLS } from '@/lib/conflictSymbols';
import {
  isMilitaryAircraft,
  isMilitaryVessel,
  MILITARY_AIRCRAFT_COLOUR,
  MILITARY_VESSEL_COLOUR,
} from '@/lib/traffic';

export type IconKind =
  | 'aircraft'
  | 'vessel'
  | 'vessel_unknown'
  | 'cyclone'
  | 'volcano'
  | 'wildfire'
  | 'thermal'
  | 'cyber'
  | 'news'
  | ConflictKind;

const ICON_SIZE = 64;

/** White-on-transparent SVG masks; deck.gl tints them with the category colour. */
const SHAPES: Record<IconKind, string> = {
  ...CONFLICT_ICON_SHAPES,
  cyber: `<g transform="scale(2.666667)">${CYBER_SHIELD_MASK}</g>`,
  news: `<g transform="scale(2.666667)">${NEWS_MASK}</g>`,
  wildfire:
    '<path d="M34 4c3 16-13 19-9 30 5-2 9-7 10-12 9 7 15 15 15 23a18 18 0 0 1-36 0c0-10 8-17 7-27 4 3 5 6 6 8C35 17 29 12 34 4Z" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
  vessel_unknown:
    '<path fill="#fff" d="M5 34h54l-9 16H17zM16 22h32v10H16zM27 12h10v8H27z"/><path d="M8 56h48" stroke="#fff" stroke-width="3"/>',
  thermal:
    '<circle cx="32" cy="32" r="9" fill="#fff"/><circle cx="32" cy="32" r="21" fill="none" stroke="#fff" stroke-width="3"/><path d="M32 2v8m0 44v8M2 32h8m44 0h8" stroke="#fff" stroke-width="3"/>',
  vessel:
    '<path fill="#fff" fill-rule="evenodd" d="M32 3 45 20v31L32 61 19 51V20z M26 24h12v18H26z"/>',
  aircraft:
    '<path fill="#fff" d="M32 4c2.4 0 4 3 4 8v12l22 13v6l-22-6v13l6 5v4l-10-3-10 3v-4l6-5V37L6 43v-6l22-13V12c0-5 1.6-8 4-8z"/>',
  cyclone:
    '<path fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" d="M32 18a14 14 0 1 1-14 14M32 46a14 14 0 1 1 14-14"/><circle cx="32" cy="32" r="4" fill="#fff"/>',
  volcano:
    '<path fill="#fff" d="M25 14h14l4 12 15 30H6l15-30zM29 20l-2 6h10l-2-6z"/><circle cx="32" cy="9" r="3" fill="#fff"/>',
};

const DATA_URIS: Record<IconKind, string> = Object.fromEntries(
  (Object.keys(SHAPES) as IconKind[]).map((kind) => [
    kind,
    `data:image/svg+xml;utf8,${encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" width="${String(ICON_SIZE)}" height="${String(ICON_SIZE)}" viewBox="0 0 ${String(ICON_SIZE)} ${String(ICON_SIZE)}">${SHAPES[kind]}</svg>`,
    )}`,
  ]),
) as Record<IconKind, string>;

/** Which icon, if any, an event should be drawn with. */
export function iconFor(event: LiveEvent): IconKind | null {
  if (event.category === 'cyber') return 'cyber';
  if (event.source_id === 'gdelt_news' && event.category === 'news') return 'news';
  if (event.category === 'conflict') return conflictKind(event);
  if (event.category === 'disaster' && ['wildfire', 'wildfires'].includes(event.subtype))
    return 'wildfire';
  if (event.category === 'disaster' && event.subtype === 'thermal_detection') return 'thermal';
  if (event.category === 'maritime' && event.subtype === 'vessel_position') {
    return typeof event.attributes.track_deg === 'number' &&
      Number.isFinite(event.attributes.track_deg)
      ? 'vessel'
      : 'vessel_unknown';
  }
  if (event.category === 'aviation') return 'aircraft';
  if (event.subtype === 'tropical_cyclone') return 'cyclone';
  if (event.subtype === 'volcano' || event.subtype === 'volcanoes') return 'volcano';
  return null;
}

/** Heading in degrees clockwise from north, when the event carries one. */
export function headingOf(event: LiveEvent): number {
  const track = event.attributes.track_deg;
  return typeof track === 'number' && Number.isFinite(track) ? track : 0;
}

export interface IconPick {
  object?: LiveEvent;
  x?: number;
  y?: number;
}

/** One icon layer for every iconed event that is located and not hidden. */
export function buildIconLayer(
  events: readonly LiveEvent[],
  onPick: (event: LiveEvent | null, position?: readonly [number, number]) => void,
  selectedId: string | null,
  globe = false,
): Layer | null {
  const data = events.filter((event) => event.point !== null && iconFor(event) !== null);
  if (data.length === 0) return null;
  return new IconLayer<LiveEvent>({
    id: 'event-icons',
    data,
    dataComparator: sameLayerRows,
    pickable: true,
    sizeUnits: 'pixels',
    // GlobeView culls back faces. Tangent icons hide the far hemisphere; their
    // Y-flipped SVG quads need clockwise winding and a 180-degree ENU correction.
    billboard: !globe,
    parameters: SYMBOL_WINDING,
    getPosition: (event) => [event.point?.lon ?? 0, event.point?.lat ?? 0],
    getIcon: (event) => ({
      url: DATA_URIS[iconFor(event) ?? 'aircraft'],
      width: ICON_SIZE,
      height: ICON_SIZE,
      mask: true,
    }),
    getSize: (event) => (event.id === selectedId ? 30 : 22),
    getColor: (event) => {
      if (iconFor(event) === 'wildfire') return [251, 146, 60, 245];
      const kind = conflictKind(event);
      return kind
        ? [...CONFLICT_SYMBOLS[kind].colour, 245]
        : event.subtype === 'emergency'
          ? [255, 90, 90, 255]
          : isMilitaryAircraft(event)
            ? MILITARY_AIRCRAFT_COLOUR
            : isMilitaryVessel(event)
              ? MILITARY_VESSEL_COLOUR
              : [...CATEGORY_STYLES[event.category].colour, 235];
    },
    // deck.gl rotates anticlockwise; a track is clockwise from north.
    getAngle: (event) =>
      (globe ? 180 : 0) +
      (['aircraft', 'vessel'].includes(iconFor(event) ?? '') ? -headingOf(event) : 0),
    updateTriggers: { getSize: [selectedId], getAngle: [globe] },
    onClick: (info: IconPick) => {
      if (typeof info.x === 'number' && typeof info.y === 'number')
        onPick(info.object ?? null, [info.x, info.y]);
      else onPick(info.object ?? null);
      return true;
    },
  });
}
