import { useState } from 'react';
import { archiveMapView, createMapView, listMapViews, updateMapView } from '@/lib/api/mapViews';
import type { MapState, MapViewPage, SavedMapView } from '@/lib/api/mapViews';
import { describeError } from '@/lib/api/errors';
import { useMapRequest } from './useMapRequest';
import { scopedMutation } from '@/lib/workspaceAccess';

export function useSavedMapViews(reportId: string, version: number, initial?: SavedMapView) {
  const request = useMapRequest();
  const [active, setActive] = useState(initial ?? null);
  const [title, setTitle] = useState(initial?.revision.title ?? 'Evidence map');
  const [page, setPage] = useState<MapViewPage | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const run = async (work: (signal: AbortSignal) => Promise<void>) => {
    const signal = request();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await work(signal);
    } catch (error) {
      if (!signal.aborted) setError(describeError(error));
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  const browse = (offset = 0) =>
    run(async (signal) => {
      const result = await scopedMutation(() => listMapViews(reportId, offset, signal));
      if (!signal.aborted) setPage(result);
    });
  const save = (state: MapState, copy: boolean) =>
    run(async (signal) => {
      const body = { version_number: version, title: title.trim(), state };
      const result =
        active && !copy
          ? await updateMapView(
              active.view.id,
              { ...body, base_revision_id: active.revision.id },
              signal,
            )
          : await createMapView({ ...body, report_id: reportId }, signal);
      if (signal.aborted) return;
      setActive(result);
      setPage(null);
      setNotice(`Saved immutable revision ${result.revision.number}.`);
    });
  const archive = () =>
    run(async (signal) => {
      if (!active) return;
      await archiveMapView(active.view.id, signal);
      if (!signal.aborted) {
        setActive({ ...active, view: { ...active.view, archived: true } });
        setPage(null);
        setNotice(
          'View archived. Its existing revision links remain available to authorised users.',
        );
      }
    });
  return { active, title, setTitle, page, busy, error, notice, browse, save, archive };
}
