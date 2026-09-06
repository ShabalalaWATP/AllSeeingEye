import { useState } from 'react';
import { useLocation } from 'react-router';

import { NavigationDialog } from './NavigationDialog';

import { LeftRail } from './LeftRail';
import { TopBar } from './TopBar';

/** Local state is discarded when desktop or operations-room mode replaces this header. */
export function MobileHeader() {
  const { key } = useLocation();
  const [openedAt, setOpenedAt] = useState<string | null>(null);
  return (
    <>
      <TopBar onOpenNavigation={() => setOpenedAt(key)} />
      {openedAt === key && <MobileNavigation onClose={() => setOpenedAt(null)} />}
    </>
  );
}

export function MobileNavigation({ onClose }: { onClose: () => void }) {
  return (
    <NavigationDialog onClose={onClose}>
      <LeftRail mobile onNavigate={onClose} />
    </NavigationDialog>
  );
}
