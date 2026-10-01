/**
 * The faces of one section: the work itself, what that work has saved and, for research,
 * its progress. Each section keeps its own saved reports, so an analyst looks for a past
 * answer where they asked the question. The tab lists live with the rest of the
 * navigation definition in `@/lib/workspaceNavigation`.
 */
import { NavLink } from 'react-router';

import type { WorkspaceView } from '@/lib/workspaceNavigation';

export type SectionTab = WorkspaceView;

export { geolocationTabs, researchTabs, subscriptionTabs } from '@/lib/workspaceNavigation';

/**
 * A tab that is the start of another tab's address matches only exactly; any other tab
 * also stays current on its detail pages, such as one research job under progress.
 */
function exactOnly(tab: SectionTab, tabs: readonly SectionTab[]): boolean {
  return tabs.some((other) => other !== tab && other.to.startsWith(`${tab.to}/`));
}

export function SectionTabs({ tabs, label }: { tabs: readonly SectionTab[]; label: string }) {
  return (
    <nav aria-label={label} className="flex flex-wrap gap-x-5 gap-y-1 border-b border-line">
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={exactOnly(tab, tabs)}
          className={({ isActive }) =>
            `border-b-2 py-3 text-sm transition-colors ${
              isActive
                ? 'border-ember text-text'
                : 'border-transparent text-muted hover:border-line hover:text-text'
            }`
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}
