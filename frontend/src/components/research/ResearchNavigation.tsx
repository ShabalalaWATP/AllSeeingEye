import { Tabs } from '@/components/ui/Tabs';
import { researchTabs } from '@/lib/workspaceNavigation';

/** Research's own tabs, the same list and name on every research page. */
export function ResearchNavigation() {
  return <Tabs links={researchTabs} label="Research" />;
}
