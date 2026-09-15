import { Link, Navigate, useSearchParams } from 'react-router';

import { ProfileSecurity } from '@/components/account/ProfileSecurity';
import { useAuthStore } from '@/stores/auth';

import { ChangePasswordForm } from './ChangePasswordForm';
import { DirectoryProfile } from './DirectoryProfile';
import { ProfilePreferences } from './ProfilePreferences';

const sections = [
  { id: 'profile', label: 'Profile', detail: 'Your identity and region' },
  { id: 'directory', label: 'Directory profile', detail: 'Optional team discovery' },
  { id: 'security', label: 'Security', detail: 'Sign-in and active sessions' },
] as const;
export type ProfileSection = (typeof sections)[number]['id'];

/** Personal settings are available to every role, separate from administration. */
export default function AccountPage() {
  const user = useAuthStore((state) => state.user);
  const [params] = useSearchParams();
  const selected = sections.find((item) => item.id === params.get('section')) ?? sections[0];
  if (!user) return null;
  const legacySection = params.get('section');
  if (legacySection === 'research' || legacySection === 'reports')
    return <Navigate to={`/settings?section=${legacySection}`} replace />;
  const initials = user.display_name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('');
  return (
    <section className="h-full overflow-y-auto p-4 sm:p-8">
      <div className="mx-auto max-w-5xl">
        <header className="flex items-center gap-4 border-b border-line pb-7">
          <span
            aria-hidden="true"
            className="flex size-14 shrink-0 items-center justify-center rounded-full border border-line bg-surface-2 text-lg font-medium uppercase text-ember"
          >
            {initials}
          </span>
          <div className="min-w-0">
            <p className="font-mono text-xs uppercase tracking-widest text-muted">Your profile</p>
            <h1 className="mt-1 text-2xl font-semibold">Account</h1>
            <p className="mt-1 break-all text-sm text-muted">{user.email}</p>
          </div>
          <span className="ml-auto hidden text-xs capitalize text-muted sm:block">{user.role}</span>
        </header>
        <div className="grid gap-8 py-7 md:grid-cols-[210px_minmax(0,1fr)] md:gap-12">
          <nav
            aria-label="Account settings"
            className="flex gap-1 overflow-x-auto md:flex-col md:self-start"
          >
            {sections.map((item) => (
              <Link
                key={item.id}
                to={`?section=${item.id}`}
                aria-current={selected.id === item.id ? 'page' : undefined}
                className={`min-h-11 shrink-0 rounded-md px-3 py-3 text-sm transition-colors ${selected.id === item.id ? 'bg-surface-2 text-ember' : 'text-muted hover:bg-surface-2 hover:text-text'}`}
              >
                <span className="block font-medium">{item.label}</span>
                <span className="mt-1 hidden text-xs text-muted md:block">{item.detail}</span>
              </Link>
            ))}
            <Link
              to="/teams"
              className="min-h-11 shrink-0 rounded-md px-3 py-3 text-sm text-muted hover:text-text md:mt-5"
            >
              View your teams
            </Link>
            <Link
              to="/settings"
              className="min-h-11 shrink-0 rounded-md px-3 py-3 text-sm text-muted hover:text-text"
            >
              Personal settings
            </Link>
          </nav>
          <div className="min-w-0" key={user.id}>
            {selected.id === 'security' ? (
              <div className="flex flex-col gap-8">
                <header>
                  <h2 className="text-xl font-semibold">Security</h2>
                  <p className="mt-2 text-sm text-muted">
                    Control how you sign in and where your account is active.
                  </p>
                </header>
                <ProfileSecurity />
                <ChangePasswordForm key={`${user.id}:${user.role}`} actorId={user.id} />
              </div>
            ) : selected.id === 'directory' ? (
              <DirectoryProfile />
            ) : (
              <ProfilePreferences key={selected.id} section={selected.id} />
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
