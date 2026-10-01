import { Link } from 'react-router';

import { helpDestination } from '@/lib/workspaceNavigation';
import { useAuthStore } from '@/stores/auth';

import { HelpIcon, ProfileIcon, SettingsIcon } from './accountIcons';

const linkClass =
  'inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-md px-2 text-muted hover:bg-surface-2 hover:text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember';

/** Personal controls and Help stay separate from the research and administrator menus. */
export function PersonalLinks() {
  const user = useAuthStore((state) => state.user);
  return (
    <>
      <Link
        to="/account"
        // Wider screens show the display name, so the name carries it too (WCAG 2.5.3).
        aria-label={user === null ? 'Your profile' : `Your profile: ${user.display_name}`}
        title="Your profile"
        className={linkClass}
      >
        <ProfileIcon />
        <span className="hidden max-w-40 truncate md:inline">{user?.display_name}</span>
      </Link>
      <Link to="/settings" aria-label="Your settings" title="Your settings" className={linkClass}>
        <SettingsIcon />
      </Link>
      <Link
        to={helpDestination.to}
        aria-label={helpDestination.label}
        title={helpDestination.label}
        className={linkClass}
      >
        <HelpIcon />
      </Link>
    </>
  );
}
