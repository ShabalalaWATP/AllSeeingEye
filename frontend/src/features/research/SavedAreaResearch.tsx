import { useCallback } from 'react';
import { fetchMapView } from '@/lib/api/mapViews';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useMapRequest } from '@/components/maps/useMapRequest';
import type { Profile } from '@/lib/api/profile';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { ApiError, describeError } from '@/lib/api/errors';
import { AreaResearchForm } from './AreaResearchForm';

export function SavedAreaResearch({
  viewId,
  revisionId,
  preferences,
  workspaces,
}: {
  viewId: string;
  revisionId: string;
  preferences: Profile;
  workspaces: Workspaces;
}) {
  const begin = useMapRequest();
  const loader = useCallback(async () => {
    if (!viewId || !revisionId)
      throw new ApiError(422, 'invalid_request', 'Choose an exact saved map revision.');
    const saved = await fetchMapView(viewId, revisionId, begin());
    if (saved.view.id !== viewId || saved.revision.id !== revisionId || !saved.revision.state.aoi)
      throw new ApiError(
        422,
        'invalid_request',
        'This saved revision does not identify a research area.',
      );
    return saved;
  }, [viewId, revisionId, begin]);
  const resource = useScopedResource(loader);
  if (resource.loading) return <LoadingNote label="Loading saved research area" />;
  if (resource.error) return <Alert tone="error">{describeError(resource.error)}</Alert>;
  return resource.data ? (
    <AreaResearchForm
      key={`${resource.key}:${revisionId}`}
      saved={resource.data}
      preferences={preferences}
      workspaces={workspaces}
    />
  ) : null;
}
