import { useCallback, useState } from 'react';
import type { MapBounds } from '@/lib/map/MapEngine';
import type { Position } from '@/lib/map/geoJsonTypes';
import { boundsFromCorners, rectangleArea } from '@/lib/map/areaGeometry';
import type { MapState } from '@/lib/api/mapViews';

type Draft = Record<keyof MapBounds, string>;
const empty = (): Draft => ({ west: '', south: '', east: '', north: '' });
const draftOf = (bounds: MapBounds): Draft => ({
  west: String(bounds.west),
  south: String(bounds.south),
  east: String(bounds.east),
  north: String(bounds.north),
});
const message = (error: unknown) =>
  error instanceof Error ? error.message : 'The area could not be selected.';
interface Selection {
  draft: Draft;
  dirty: boolean;
  picking: boolean;
  first: Position | null;
  error: string | null;
  origin: string | null;
}
const initial = (): Selection => ({
  draft: empty(),
  dirty: false,
  picking: false,
  first: null,
  error: null,
  origin: null,
});

export function useAreaSelection(onChange: (area: MapState['aoi']) => void) {
  const [selection, setSelection] = useState(initial);
  const cancel = useCallback(() => setSelection(initial()), []);
  const pick = useCallback(
    (point: Position) =>
      setSelection((previous) => {
        if (!previous.picking) return previous;
        if (!previous.first) return { ...previous, first: point };
        try {
          return {
            ...previous,
            draft: draftOf(boundsFromCorners(previous.first, point)),
            picking: false,
            first: null,
            error: null,
            origin:
              'Two corners use the shorter longitude span. Review the bounds before applying.',
          };
        } catch (error) {
          return { ...previous, first: null, error: message(error) };
        }
      }),
    [],
  );
  const viewport = (read: () => MapBounds | null) => {
    try {
      const bounds = read();
      if (!bounds) throw new Error('Open a supported map before capturing its viewport.');
      rectangleArea(bounds);
      setSelection({
        ...initial(),
        draft: draftOf(bounds),
        dirty: true,
        origin:
          'Viewport bounding envelope, not an exact visible-ground polygon. Review the bounds before applying.',
      });
    } catch (error) {
      setSelection((value) => ({ ...value, error: message(error) }));
    }
  };
  const apply = () => {
    try {
      if (Object.values(selection.draft).some((value) => !value.trim()))
        throw new Error('Enter all four area bounds.');
      const { west, east, south, north } = selection.draft;
      const canonical = rectangleArea({
        west: Number(west),
        east: Number(east),
        south: Number(south),
        north: Number(north),
      });
      onChange({ ...canonical });
      setSelection((value) => ({
        ...value,
        dirty: false,
        picking: false,
        first: null,
        error: null,
      }));
    } catch (error) {
      setSelection((value) => ({ ...value, error: message(error) }));
    }
  };
  return {
    ...selection,
    pick,
    viewport,
    apply,
    edit: (field: keyof MapBounds, value: string) =>
      setSelection((previous) => ({
        ...previous,
        draft: { ...previous.draft, [field]: value },
        dirty: true,
        picking: false,
        first: null,
        error: null,
        origin: 'Numeric WGS84 bounds.',
      })),
    start: () =>
      setSelection((value) => ({
        ...value,
        picking: true,
        first: null,
        dirty: true,
        error: null,
        origin: null,
      })),
    cancel,
    clear: () => {
      onChange(null);
      setSelection(initial());
    },
  };
}
