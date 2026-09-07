import { useEffect, useMemo, useState } from 'react';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import type { Position } from '@/lib/map/geoJsonTypes';
import { MAX_MEASUREMENT_POINTS, measurementPoint, measurementText } from '@/lib/map/measurements';
import type { MeasurementMode } from '@/lib/map/measurements';
import type { GlobeEngineHandle } from './useGlobeEngine';

export function useMapMeasurement(engine: Pick<GlobeEngineHandle, 'onClick'>, enabled: boolean) {
  const [points, setPoints] = useState<Position[]>([]);
  const [mode, setMode] = useState<MeasurementMode>('distance');
  const [picking, setPicking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetSequence, setResetSequence] = useState(0);
  useEffect(() => {
    const clear = () => {
      setResetSequence((previous) => previous + 1);
      setPoints([]);
      setPicking(false);
      setError(null);
    };
    const offAccess = subscribeWorkspaceAccess(clear);
    const offUser = useAuthStore.subscribe((next, previous) => {
      if (next.user?.id !== previous.user?.id) clear();
    });
    return () => {
      offAccess();
      offUser();
    };
  }, []);
  useEffect(
    () =>
      engine.onClick(({ lon, lat }) => {
        if (!picking || !enabled) return;
        setPoints((previous) =>
          previous.length >= MAX_MEASUREMENT_POINTS
            ? previous
            : [...previous, measurementPoint(lon, lat)],
        );
      }),
    [engine, picking, enabled],
  );
  const result = useMemo(() => measurementText(points, mode), [points, mode]);
  return {
    points,
    mode,
    setMode,
    picking: picking && enabled,
    setPicking,
    error,
    result,
    resetSequence,
    canPick: enabled,
    add: (lon: number, lat: number) => {
      try {
        if (points.length >= MAX_MEASUREMENT_POINTS)
          throw new Error('At most 32 measurement points.');
        const point = measurementPoint(lon, lat);
        setPoints((previous) =>
          previous.length >= MAX_MEASUREMENT_POINTS ? previous : [...previous, point],
        );
        setError(null);
      } catch (value) {
        setError(value instanceof Error ? value.message : 'Invalid coordinate.');
      }
    },
    undo: () => {
      setPoints((previous) => previous.slice(0, -1));
      setError(null);
    },
    clear: () => {
      setPoints([]);
      setPicking(false);
      setError(null);
    },
  };
}
export type MapMeasurement = ReturnType<typeof useMapMeasurement>;
