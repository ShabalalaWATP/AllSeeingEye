import { useEffect } from 'react';

import { useGlobeStore } from '@/stores/globe';

/**
 * The ops room only exists on the map home. Leaving it by any route (the palette, a link
 * or history) ends it, so returning to `/` later does not drop back into the wall screen.
 * Entering from elsewhere navigates first, so arriving at `/` never ends it.
 */
export function useOpsRoomRoute(pathname: string): void {
  useEffect(() => {
    if (pathname !== '/' && useGlobeStore.getState().opsRoom)
      useGlobeStore.getState().setOpsRoom(false);
  }, [pathname]);
}
