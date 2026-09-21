import { useEffect } from 'react';

import { getMyResearchUsage } from '@/lib/api/researchUsage';
import { subscribeResearchUsage } from '@/lib/researchUsageEvents';

import { useScopedResource } from './useScopedResource';

/** Keep mounted usage views current when scheduled work runs or a UTC period resets. */
export function useResearchAllowance() {
  const resource = useScopedResource(getMyResearchUsage);
  const { refresh } = resource;
  useEffect(() => {
    const update = () => {
      void refresh();
    };
    const updateVisible = () => {
      if (document.visibilityState === 'visible') update();
    };
    const unsubscribe = subscribeResearchUsage(update);
    window.addEventListener('focus', updateVisible);
    document.addEventListener('visibilitychange', updateVisible);
    const timer = window.setInterval(updateVisible, 60_000);
    return () => {
      unsubscribe();
      window.removeEventListener('focus', updateVisible);
      document.removeEventListener('visibilitychange', updateVisible);
      window.clearInterval(timer);
    };
  }, [refresh]);
  return resource;
}
