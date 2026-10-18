import { useMemo } from 'react';

import { useSiteFacts } from '@/lib/useSiteFacts';
import { useWorkspaceReturnStore } from '@/stores/workspaceReturn';

import { adminCommandTargets } from './adminCommandTargets';
import { CommandPalette } from './CommandPalette';

/** The palette inside administration: administration pages and the way back to research. */
export function AdminPalette() {
  const researchTo = useWorkspaceReturnStore((state) => state.research);
  const site = useSiteFacts();
  const enquiries = site.status === 'ready' && site.facts.enterprise_enquiries_enabled;
  const targets = useMemo(
    () => adminCommandTargets({ researchTo, enquiries }),
    [researchTo, enquiries],
  );
  return <CommandPalette targets={targets} searchLabel="Search administration pages" />;
}
