import { useCallback, useEffect, useRef, useState } from 'react';
import type { Position } from '@/lib/map/geoJsonTypes';
import type { RfMapEstimate } from '@/lib/map/rfMap';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { createRfDraft } from '@/lib/map/rfDraft';
import { rfPositionSchema, type RfSiteKind, type RfSiteNames } from '@/lib/map/rfSites';
import type { RfStudySnapshot } from '@/lib/map/rfStudy';
import type { RfDraft } from '@/lib/map/rfDraft';
import { measure, measurementPoint } from '@/lib/map/measurements';
import { subscribeRfWorkspaceReset } from '@/lib/map/rfWorkspaceAccess';
import type { GlobeEngineHandle } from './useGlobeEngine';

/** Local planning positions are cleared with the authenticated workspace. */
export function useRfMapPlacement(engine: GlobeEngineHandle, enabled: boolean) {
  const [origin, setOrigin] = useState<Position | null>(null);
  const [receiver, setReceiver] = useState<Position | null>(null);
  const [picking, setPicking] = useState<'origin' | 'receiver' | null>(null);
  const [interaction, setInteraction] = useState<'click' | 'drag'>('click');
  const [preview, setPreview] = useState<{ kind: RfSiteKind; point: Position } | null>(null);
  const dragging = useRef(false);
  const cancelDrag = useCallback(() => {
    dragging.current = false;
    setPreview(null);
  }, []);
  const [estimate, setEstimate] = useState<RfMapEstimate | null>(null);
  const [analysis, setAnalysis] = useState<RfAnalysis | null>(null);
  const [draft, setDraft] = useState(() => createRfDraft());
  const [siteNames, setSiteNames] = useState<RfSiteNames>({ origin: '', receiver: '' });
  const [baseline, setBaseline] = useState<RfStudySnapshot | null>(null);
  const [profilePoint, setProfilePoint] = useState<Position | null>(null);
  const [coverageBubble, setCoverageBubble] = useState(false);
  useEffect(() => {
    const clear = () => {
      cancelDrag();
      setInteraction('click');
      setSiteNames({ origin: '', receiver: '' });
      setBaseline(null);
      setProfilePoint(null);
      setOrigin(null);
      setReceiver(null);
      setPicking(null);
      setEstimate(null);
      setAnalysis(null);
      setDraft(createRfDraft());
      setCoverageBubble(false);
    };
    return subscribeRfWorkspaceReset(clear);
  }, [cancelDrag]);
  useEffect(
    () =>
      engine.onClick(({ lon, lat }) => {
        if (!enabled || !picking || interaction !== 'click') return;
        try {
          const point = measurementPoint(lon, lat);
          if (picking === 'origin') setOrigin(point);
          else setReceiver(point);
          setProfilePoint(null);
          setEstimate(null);
          setAnalysis(null);
          setPicking(null);
        } catch {
          /* Invalid globe-sky clicks leave placement armed. */
        }
      }),
    [engine, enabled, picking, interaction],
  );
  useEffect(
    () =>
      engine.onDrag?.((event) => {
        if (!enabled || !picking || interaction !== 'drag') return;
        const site = picking === 'origin' ? origin : receiver;
        if (event.phase === 'cancel') {
          cancelDrag();
          setPicking(null);
          return;
        }
        try {
          const point = measurementPoint(event.current.lon, event.current.lat);
          if (event.phase === 'start') {
            cancelDrag();
            if (!site) return;
            const start = measurementPoint(event.start.lon, event.start.lat);
            const metresPerPixel =
              (40075016.686 * Math.max(0.05, Math.cos((site[1] * Math.PI) / 180))) /
              (512 * 2 ** engine.getZoom());
            if (measure([site, start], 'distance').metres > metresPerPixel * 16) return;
            dragging.current = true;
            setAnalysis(null);
            setEstimate(null);
            setProfilePoint(null);
          }
          if (!dragging.current) return;
          if (event.phase === 'end') {
            if (picking === 'origin') setOrigin(point);
            else setReceiver(point);
            cancelDrag();
            setPicking(null);
          } else setPreview({ kind: picking, point });
        } catch {
          cancelDrag();
          setPicking(null);
        }
      }),
    [engine, enabled, picking, interaction, origin, receiver, cancelDrag],
  );
  useEffect(() => {
    if (!enabled || !picking) return;
    const cancel = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        cancelDrag();
        setPicking(null);
      }
    };
    window.addEventListener('keydown', cancel);
    return () => window.removeEventListener('keydown', cancel);
  }, [enabled, picking, cancelDrag]);
  const setSite = (kind: RfSiteKind, point: Position, name?: string) => {
    const valid = rfPositionSchema.parse(point);
    cancelDrag();
    if (kind === 'origin') setOrigin(valid);
    else setReceiver(valid);
    if (name !== undefined)
      setSiteNames((previous) => ({ ...previous, [kind]: name.trim().slice(0, 80) }));
    if (kind === 'receiver') setDraft((previous) => ({ ...previous, study: 'link' }));
    setAnalysis(null);
    setEstimate(null);
    setProfilePoint(null);
    setPicking(null);
  };
  return {
    interaction,
    canDrag: engine.onDrag !== undefined,
    setDragSite: (kind: RfSiteKind) => {
      if (!engine.onDrag || !(kind === 'origin' ? origin : receiver)) return;
      cancelDrag();
      setInteraction('drag');
      setPicking(kind);
    },
    siteNames,
    baseline,
    setBaseline,
    profilePoint,
    setProfilePoint,
    setSite,
    swapSites: () => {
      cancelDrag();
      if (!origin || !receiver) return;
      setOrigin(receiver);
      setReceiver(origin);
      setSiteNames((previous) => ({ origin: previous.receiver, receiver: previous.origin }));
      setAnalysis(null);
      setEstimate(null);
      setProfilePoint(null);
      setPicking(null);
    },
    restoreStudy: (study: RfStudySnapshot) => {
      cancelDrag();
      setOrigin(study.origin);
      setReceiver(study.receiver);
      setSiteNames(study.siteNames);
      setDraft(study.draft);
      setBaseline(study);
      setAnalysis(null);
      setEstimate(null);
      setProfilePoint(null);
      setPicking(null);
    },
    origin: enabled && picking === 'origin' && preview?.kind === 'origin' ? preview.point : origin,
    receiver:
      enabled && picking === 'receiver' && preview?.kind === 'receiver' ? preview.point : receiver,
    picking: enabled ? picking : null,
    setPicking: (next: RfSiteKind | null) => {
      cancelDrag();
      setInteraction('click');
      setPicking(next);
    },
    estimate,
    setEstimate: (next: RfMapEstimate | null) => {
      setEstimate(next);
      if (next) setAnalysis(null);
    },
    analysis,
    setAnalysis: (next: RfAnalysis | null) => {
      setProfilePoint(null);
      setAnalysis(next);
      if (next) setEstimate(null);
    },
    draft,
    coverageBubble,
    setCoverageBubble,
    setDraft: (next: RfDraft) => {
      setProfilePoint(null);
      setDraft(next);
      setEstimate(null);
      setAnalysis(null);
    },
    clearSites: () => {
      cancelDrag();
      setOrigin(null);
      setReceiver(null);
      setSiteNames({ origin: '', receiver: '' });
      setPicking(null);
      setProfilePoint(null);
      setAnalysis(null);
      setEstimate(null);
      setBaseline(null);
    },
    clearReceiver: () => {
      cancelDrag();
      setProfilePoint(null);
      setReceiver(null);
      setDraft((previous) => ({ ...previous, study: 'area' }));
      setEstimate(null);
      setAnalysis(null);
      setPicking(null);
    },
  };
}
