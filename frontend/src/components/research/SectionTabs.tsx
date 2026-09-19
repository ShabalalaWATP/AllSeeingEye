/**
 * The two faces of one section: the work itself, and what that work has saved. Each
 * section keeps its own saved reports, so an analyst looks for a past answer where
 * they asked the question.
 */
import { NavLink } from 'react-router';

export interface SectionTab {
  readonly to: string;
  readonly label: string;
}

export function SectionTabs({ tabs, label }: { tabs: readonly SectionTab[]; label: string }) {
  return (
    <nav aria-label={label} className="flex flex-wrap gap-x-5 gap-y-1 border-b border-line">
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end
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

export const researchTabs: readonly SectionTab[] = [
  { to: '/research', label: 'New research' },
  { to: '/research/saved', label: 'Saved research' },
];

export const subscriptionTabs: readonly SectionTab[] = [
  { to: '/subscriptions', label: 'Subscriptions' },
  { to: '/subscriptions/saved', label: 'Saved updates' },
];

export const geolocationTabs: readonly SectionTab[] = [
  { to: '/geolocation', label: 'New assessment' },
  { to: '/geolocation/saved', label: 'Saved assessments' },
];
