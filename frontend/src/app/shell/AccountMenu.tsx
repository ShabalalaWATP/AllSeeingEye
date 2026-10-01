import { Link } from 'react-router';

import { useAuthStore } from '@/stores/auth';

import { ProfileIcon, SettingsIcon } from './accountIcons';
import { useMenuButton } from './useMenuButton';
import { useSignOut } from './useSignOut';

const triggerClass =
  'inline-flex min-h-11 min-w-11 items-center justify-center rounded-md px-2 text-muted hover:bg-surface-2 hover:text-text aria-expanded:bg-surface-2 aria-expanded:text-text';
const itemClass =
  'flex min-h-11 w-full items-center gap-3 rounded-md px-3 text-left text-sm text-text hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-60';

function signOutStatus(busy: boolean, failed: boolean): string {
  if (busy) return 'Signing out…';
  return failed ? 'Sign-out did not finish. Try again.' : '';
}

/**
 * Narrow screens keep the bell and navigation in the top bar and gather the personal
 * links and Logout here. Only activating Logout signs out; opening or dismissing never does.
 */
export function AccountMenu() {
  const displayName = useAuthStore((state) => state.user?.display_name);
  const { open, toggle, close, menuId, wrapperRef, triggerRef, menuRef } = useMenuButton();
  const { signOut, busy, failed } = useSignOut();

  return (
    <div ref={wrapperRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-label="Account menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        title="Account"
        onClick={toggle}
        className={triggerClass}
      >
        <ProfileIcon />
      </button>
      {open && (
        <div
          ref={menuRef}
          id={menuId}
          className="absolute top-full right-0 z-40 mt-2 w-60 max-w-[calc(100vw-1rem)] rounded-lg border border-line bg-ground p-1 text-text shadow-card"
        >
          {displayName !== undefined && (
            <p className="truncate px-3 pt-2 pb-1 text-xs text-muted">{displayName}</p>
          )}
          <ul aria-label="Account" className="flex flex-col">
            <li>
              <Link to="/account" onClick={close} className={itemClass}>
                <ProfileIcon />
                Your profile
              </Link>
            </li>
            <li>
              <Link to="/settings" onClick={close} className={itemClass}>
                <SettingsIcon />
                Your settings
              </Link>
            </li>
            <li className="mt-1 border-t border-line/70 pt-1">
              <button
                type="button"
                aria-busy={busy}
                disabled={busy}
                onClick={() => void signOut()}
                className={itemClass}
              >
                Logout
              </button>
            </li>
          </ul>
          <p role="status" className="px-3 text-xs text-muted empty:hidden">
            {signOutStatus(busy, failed)}
          </p>
        </div>
      )}
    </div>
  );
}
