import { researchTabs } from '@/lib/workspaceNavigation';

import { SectionTabs } from './SectionTabs';

/** Research's own tabs, the same list and name on every research page. */
export function ResearchNavigation() {
  return <SectionTabs tabs={researchTabs} label="Research" />;
}
