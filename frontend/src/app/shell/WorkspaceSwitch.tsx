import { Link } from 'react-router';

import { selectIsAdmin, useAuthStore } from '@/stores/auth';
import { useWorkspaceReturnStore } from '@/stores/workspaceReturn';

import { RailIcon } from './railIcons';

export type Workspace = 'research' | 'admin';

const SWITCHES = {
  research: { label: 'Research', name: 'Go to research workspace', icon: 'map' },
  admin: { label: 'Administration', name: 'Go to Administration', icon: 'admin' },
} as const;

/**
 * One tap to the other workspace, returning to where the administrator last was there.
 * Renders nothing, and links to nothing, for anyone who is not a current administrator.
 */
export function WorkspaceSwitch({ to }: { to: Workspace }) {
  const isAdmin = useAuthStore(selectIsAdmin);
  const target = useWorkspaceReturnStore((state) =>
    to === 'admin' ? state.admin : state.research,
  );
  if (!isAdmin) return null;
  const { label, name, icon } = SWITCHES[to];
  return (
    <Link
      to={target}
      aria-label={name}
      title={name}
      data-workspace-switch={to}
      className="inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center gap-2 rounded-md border border-line/70 px-2 text-sm text-text hover:border-ember/50 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember"
    >
      <RailIcon name={icon} className="text-ember" />
      {/* Phones show the icon alone; the accessible name and title still say where it goes. */}
      <span className="hidden sm:inline">{label}</span>
    </Link>
  );
}
