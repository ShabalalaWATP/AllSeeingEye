import { useCallback, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { ApiError, describeError } from '@/lib/api/errors';
import { fetchBrief } from '@/lib/api/researchBriefs';
import { fetchMapView } from '@/lib/api/mapViews';
import { fetchReport } from '@/lib/api/reports';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { draftFromBrief, newBriefDraft } from '@/lib/researchBriefDraft';

import { BriefEditor, type InitialBrief } from './BriefEditor';
import { BriefLibrary } from './BriefLibrary';

export function BriefWorkspace({
  briefId,
  revision,
  mapViewId,
  mapRevisionId,
  fromReportId,
  fromReportVersion,
  initialQuestion,
  intent,
}: {
  briefId: string;
  revision?: number | undefined;
  mapViewId?: string | undefined;
  mapRevisionId?: string | undefined;
  fromReportId?: string | undefined;
  fromReportVersion?: number | undefined;
  initialQuestion?: string | undefined;
  intent?: 'subscribe' | undefined;
}) {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  const loader = useCallback(async (): Promise<InitialBrief> => {
    const controller = new AbortController();
    request.current?.abort();
    request.current = controller;
    if (briefId === 'library')
      return { brief: null, draft: newBriefDraft(), copy: false, mapTitle: null };
    if (briefId !== 'new') {
      if (fromReportId) {
        if (!fromReportVersion || !revision)
          throw new ApiError(
            422,
            'invalid_report_link',
            'Choose an exact report and brief revision.',
          );
        const report = await fetchReport(fromReportId, fromReportVersion, controller.signal);
        if (
          report.version.number !== fromReportVersion ||
          report.version.brief_id !== briefId ||
          report.version.brief_revision !== revision
        )
          throw new ApiError(
            422,
            'invalid_report_link',
            'This report edition has a different frozen brief.',
          );
      }
      const brief = await fetchBrief(briefId, revision, controller.signal);
      const draft = draftFromBrief(brief);
      if (fromReportId && fromReportVersion) {
        draft.scope.origin_report_id = fromReportId;
        draft.scope.origin_version = fromReportVersion;
        draft.scope.parent_report_id = null;
        draft.scope.parent_version = null;
      }
      return {
        brief,
        draft,
        copy: !!fromReportId,
        mapTitle: null,
      };
    }
    const draft = newBriefDraft();
    if (initialQuestion) draft.question.main = initialQuestion;
    if (mapViewId || mapRevisionId) {
      if (!mapViewId || !mapRevisionId)
        throw new ApiError(422, 'invalid_map_link', 'Choose an exact saved map revision.');
      const map = await fetchMapView(mapViewId, mapRevisionId, controller.signal);
      if (map.view.id !== mapViewId || map.revision.id !== mapRevisionId || !map.revision.state.aoi)
        throw new ApiError(
          422,
          'invalid_map_link',
          'This saved map revision has no research polygon.',
        );
      draft.team_id = map.view.team_id;
      draft.scope.map_view_id = mapViewId;
      draft.scope.map_revision_id = mapRevisionId;
      draft.title = map.revision.title;
      return { brief: null, draft, copy: false, mapTitle: map.revision.title };
    }
    return { brief: null, draft, copy: false, mapTitle: null };
  }, [
    briefId,
    revision,
    mapViewId,
    mapRevisionId,
    fromReportId,
    fromReportVersion,
    initialQuestion,
  ]);
  const resource = useScopedResource(loader);
  const { data, loading, error, reload } = resource;
  if (loading) return <LoadingNote label="Loading Research Brief" />;
  if (error)
    return (
      <Alert tone="error">
        {describeError(error)}{' '}
        <Button variant="secondary" onClick={() => void reload()}>
          Retry brief
        </Button>
      </Alert>
    );
  if (!data) return null;
  if (briefId === 'library') return <BriefLibrary />;
  return (
    <BriefEditor
      key={`${resource.key}:${briefId}:${revision ?? ''}:${mapRevisionId ?? ''}`}
      initial={data}
      fromReportId={fromReportId}
      fromReportVersion={fromReportVersion}
      intent={intent}
      initialStep={params.get('stage') === 'run' ? 'run' : undefined}
      onSaved={(brief) =>
        void navigate(
          `/research?brief=${brief.identity.id}&revision=${brief.identity.revision}&stage=run${intent === 'subscribe' ? '&intent=subscribe' : ''}`,
          {
            replace: true,
          },
        )
      }
    />
  );
}
