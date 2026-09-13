import { useCallback, useMemo, useRef } from 'react';

import type { LiveEvent } from '@/lib/api/eventSchemas';

import { ConnectivityPanelView } from './context/ConnectivityPanel';
import type { useNetworkMap } from './useNetworkMap';
import type { useInfrastructure } from './infrastructure/useInfrastructure';

/** One Technology control, sharing the connectivity snapshot with its map layer. */
export function useTechnologyControl(
  network: ReturnType<typeof useNetworkMap>,
  infrastructure: ReturnType<typeof useInfrastructure>,
  country: string | null,
  onSelect: (event: LiveEvent) => void,
) {
  const activated = useRef(false);
  const enableTechnology = infrastructure.enableTechnology;
  const setEnabled = network.setEnabled;
  const open = network.open;
  const activate = useCallback(() => {
    if (activated.current) return;
    activated.current = true;
    enableTechnology();
    setEnabled(true);
  }, [enableTechnology, setEnabled]);
  const { snapshot, groups } = network;
  return useMemo(
    () => ({
      activate,
      connectivityEnabled: open,
      toggleConnectivity: () => setEnabled(!open),
      connectivityCount: groups.length,
      connectivity: (
        <ConnectivityPanelView
          country={country}
          onSelect={onSelect}
          snapshot={snapshot}
          mappedCount={groups.length}
        />
      ),
    }),
    [activate, open, setEnabled, country, onSelect, snapshot, groups.length],
  );
}
