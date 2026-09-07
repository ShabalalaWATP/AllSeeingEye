import { useMemo, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { MapState } from '@/lib/api/mapViews';
import { MAX_MEASUREMENT_POINTS, measurementPoint, measurementText } from '@/lib/map/measurements';
import type { MeasurementMode } from '@/lib/map/measurements';
import { hasWebGl2 } from '@/lib/map/webgl';

const method = 'wgs84-geographiclib-2.2.0-v1' as const;
/** Original coordinates are revision state; results are always derived with the recorded method. */
export function useReportMeasurement(
  state: MapState,
  setState: Dispatch<SetStateAction<MapState>>,
  opened: boolean,
) {
  const [picking, setPicking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetSequence, setResetSequence] = useState(0);
  const supported = useMemo(() => hasWebGl2(), []);
  const points = state.measurement?.points ?? [];
  const mode = state.measurement?.mode ?? 'distance';
  const update = (
    change: (value: NonNullable<MapState['measurement']>) => MapState['measurement'],
  ) =>
    setState((previous) => ({
      ...previous,
      measurement: change(previous.measurement ?? { points: [], mode: 'distance', method }),
    }));
  return {
    points,
    mode,
    setMode: (mode: MeasurementMode) => update((value) => ({ ...value, mode })),
    picking: picking && opened && supported,
    setPicking,
    error,
    result: measurementText(points, mode),
    resetSequence,
    canPick: opened && supported,
    add: (longitude: number, latitude: number) => {
      try {
        if (points.length >= MAX_MEASUREMENT_POINTS)
          throw new Error('At most 32 measurement points.');
        const point = measurementPoint(longitude, latitude);
        update((value) =>
          value.points.length >= MAX_MEASUREMENT_POINTS
            ? value
            : { ...value, points: [...value.points, point] },
        );
        setError(null);
      } catch (value) {
        setError(value instanceof Error ? value.message : 'Invalid coordinate.');
      }
    },
    undo: () => {
      update((value) => ({ ...value, points: value.points.slice(0, -1) }));
      setError(null);
    },
    clear: () => {
      update(() => null);
      setPicking(false);
      setError(null);
      setResetSequence((value) => value + 1);
    },
  };
}
