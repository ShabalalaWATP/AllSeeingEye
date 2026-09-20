import { useEffect, useMemo, useState } from 'react';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import { drawingAuthority } from '@/lib/map/drawingAuthority';
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
      if (drawingAuthority(next) !== drawingAuthority(previous)) clear();
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
  useEffect(() => {
    if (!picking || !enabled) return;
    const shortcut = (event: KeyboardEvent) => {
      const target = event.target;
      if (
        event.isComposing ||
        event.ctrlKey ||
        event.metaKey ||
        event.altKey ||
        (target instanceof HTMLElement &&
          (target.isContentEditable ||
            target.closest('input, textarea, select, [contenteditable="true"], [role="textbox"]')))
      )
        return;
      if (event.key === 'Escape' || event.key === 'Enter') {
        event.preventDefault();
        setPicking(false);
      } else if (event.key === 'Backspace') {
        event.preventDefault();
        setPoints((previous) => previous.slice(0, -1));
        setError(null);
      }
    };
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, [picking, enabled]);
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
