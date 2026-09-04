import { useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router';

import { useGlobeStore } from '@/stores/globe';
import type { ViewMode } from '@/stores/globe';

export interface ViewNavigation {
  mode: ViewMode;
  onGlobePage: boolean;
  showGlobe: () => void;
  showMap: () => void;
}

/** Switches the root view between globe and map, navigating home when elsewhere. */
export function useViewNavigation(): ViewNavigation {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const mode = useGlobeStore((state) => state.mode);
  const setMode = useGlobeStore((state) => state.setMode);
  const onGlobePage = pathname === '/';

  const show = useCallback(
    (next: ViewMode) => {
      setMode(next);
      if (!onGlobePage) void navigate('/');
    },
    [navigate, onGlobePage, setMode],
  );

  const showGlobe = useCallback(() => {
    show('globe');
  }, [show]);
  const showMap = useCallback(() => {
    show('map');
  }, [show]);

  return { mode, onGlobePage, showGlobe, showMap };
}
