import { NavLink } from 'react-router';

const destinations = [
  ['/research', 'New research'],
  ['/research/jobs', 'Jobs'],
  ['/research/recurring', 'Recurring'],
  ['/direction', 'Plans & areas'],
] as const;

/** Shared navigation keeps research tools together without coupling features. */
export function ResearchNavigation() {
  return (
    <nav
      aria-label="Research tools"
      className="flex flex-wrap gap-x-5 gap-y-1 border-b border-line"
    >
      {destinations.map(([to, label]) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/research'}
          className={({ isActive }) =>
            `border-b-2 py-3 text-sm transition-colors ${
              isActive
                ? 'border-ember text-text'
                : 'border-transparent text-muted hover:border-line hover:text-text'
            }`
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
