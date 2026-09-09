import { useEffect, useState } from 'react';
import type { Position } from '@/lib/map/geoJsonTypes';
import type { RfMapEstimate } from '@/lib/map/rfMap';
import { createRfDraft } from '@/lib/map/rfDraft';
import type { RfDraft } from '@/lib/map/rfDraft';
import { measurementPoint } from '@/lib/map/measurements';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import type { GlobeEngineHandle } from './useGlobeEngine';

/** Local planning positions are cleared with the authenticated workspace. */
export function useRfMapPlacement(engine: GlobeEngineHandle, enabled: boolean) {
  const [origin, setOrigin] = useState<Position | null>(null);
  const [receiver, setReceiver] = useState<Position | null>(null);
  const [picking, setPicking] = useState<'origin' | 'receiver' | null>(null);
  const [estimate, setEstimate] = useState<RfMapEstimate | null>(null);
  const [draft, setDraft] = useState(() => createRfDraft());
  useEffect(() => {
    const clear = () => {
      setOrigin(null);
      setReceiver(null);
      setPicking(null);
      setEstimate(null);
      setDraft(createRfDraft());
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
        if (!enabled || !picking) return;
        try {
          const point = measurementPoint(lon, lat);
          if (picking === 'origin') setOrigin(point);
          else setReceiver(point);
          setEstimate(null);
          setPicking(null);
        } catch {
          /* Invalid globe-sky clicks leave placement armed. */
        }
      }),
    [engine, enabled, picking],
  );
  useEffect(() => {
    if (!enabled || !picking) return;
    const cancel = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setPicking(null);
    };
    window.addEventListener('keydown', cancel);
    return () => window.removeEventListener('keydown', cancel);
  }, [enabled, picking]);
  return {
    origin,
    receiver,
    picking: enabled ? picking : null,
    setPicking,
    estimate,
    setEstimate,
    draft,
    setDraft: (next: RfDraft) => {
      setDraft(next);
      setEstimate(null);
    },
    clearReceiver: () => {
      setReceiver(null);
      setEstimate(null);
      setPicking(null);
    },
  };
}
