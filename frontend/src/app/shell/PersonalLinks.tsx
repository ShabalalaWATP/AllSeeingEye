import { Link } from 'react-router';

import { useAuthStore } from '@/stores/auth';

const linkClass =
  'inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-md px-2 text-muted hover:bg-surface-2 hover:text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember';

/** Personal controls stay separate from the research and administrator menus. */
export function PersonalLinks() {
  const user = useAuthStore((state) => state.user);
  return (
    <>
      <Link to="/account" aria-label="Your profile" title="Your profile" className={linkClass}>
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          aria-hidden="true"
        >
          <circle cx="12" cy="8" r="3.5" />
          <path d="M5 21v-2a7 7 0 0 1 14 0v2" />
        </svg>
        <span className="hidden max-w-40 truncate md:inline">{user?.display_name}</span>
      </Link>
      <Link to="/settings" aria-label="Your settings" title="Your settings" className={linkClass}>
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="m9 3-.6 2.6-2 .9L4 5.7l-2 3.5L4 11v2l-2 1.8 2 3.5 2.4-.8 2 .9L9 21h6l.6-2.6 2-.9 2.4.8 2-3.5-2-1.8v-2l2-1.8-2-3.5-2.4.8-2-.9L15 3Z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      </Link>
    </>
  );
}
