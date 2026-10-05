import { createContext, useContext } from 'react';
import type { ReactNode } from 'react';
import { useGlobePage } from './useGlobePage';
import type { GlobePageInputs, GlobePageModel } from './useGlobePage';

const EventScope = createContext<GlobePageModel | null>(null);

/**
 * Own the one live event pipeline below the shell. Children are created by the shell,
 * so event and clock updates notify consumers without rebuilding unrelated controls.
 */
export function GlobeEventScope({
  children,
  ...inputs
}: GlobePageInputs & { children: ReactNode }) {
  const page = useGlobePage(inputs);
  return <EventScope.Provider value={page}>{children}</EventScope.Provider>;
}

export function useGlobeEventScope(): GlobePageModel {
  const page = useContext(EventScope);
  if (page === null) throw new Error('Globe event views require GlobeEventScope.');
  return page;
}
