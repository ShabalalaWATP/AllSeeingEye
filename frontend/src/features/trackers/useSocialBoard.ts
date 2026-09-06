import { useNavigate } from 'react-router';

import { fetchSocialBoard } from '@/lib/api/social';
import type { SocialKeyword } from '@/lib/api/social';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';
import { useEventsStore } from '@/stores/events';

export function describeSocialActivity(row: SocialKeyword): string {
  if (row.baseline === null) return 'No baseline yet';
  if (row.baseline_hours < 6) return 'Building baseline';
  if (row.burst)
    return row.ratio === null ? 'Burst: new activity' : `Burst: ${row.ratio.toFixed(1)}× baseline`;
  return 'No burst';
}

export function useSocialBoard() {
  useWorkspaces();
  const resource = useScopedResource(fetchSocialBoard);
  const navigate = useNavigate();
  const showOnGlobe = () => {
    const state = useEventsStore.getState();
    state.setCountry(null);
    state.setWindow(24);
    if (state.hidden.includes('social')) state.toggleCategory('social');
    void navigate('/');
  };
  return { ...resource, showOnGlobe };
}
