import { Link } from 'react-router';

import { useAuthStore } from '@/stores/auth';

import { ChangePasswordForm } from './ChangePasswordForm';

/** Personal identity is read from the current session, with no role-editing surface. */
export default function AccountPage() {
  const user = useAuthStore((state) => state.user);
  if (!user) return null;
  return (
    <section className="h-full overflow-y-auto p-4 sm:p-6">
      <div className="mx-auto flex max-w-2xl flex-col gap-8">
        <header>
          <p className="font-mono text-xs uppercase tracking-widest text-muted">Your profile</p>
          <h1 className="mt-2 text-2xl font-semibold">Account</h1>
        </header>
        <dl className="grid gap-5 border-y border-line py-5 sm:grid-cols-2">
          <div>
            <dt className="text-xs text-muted">Name</dt>
            <dd className="mt-1 break-words">{user.display_name}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Email</dt>
            <dd className="mt-1 break-all">{user.email}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Account role</dt>
            <dd className="mt-1 capitalize">{user.role}</dd>
          </div>
          <div className="self-end">
            <Link
              to="/teams"
              className="inline-flex min-h-11 items-center rounded text-sm text-ember hover:underline"
            >
              View your teams
            </Link>
          </div>
        </dl>
        <section className="border-b border-line pb-6">
          <h2 className="text-xl font-semibold">Multi-factor authentication</h2>
          <p className="mt-2 text-sm text-muted">
            Protect your account with email verification or an authenticator app.
          </p>
          <Link
            to="/account/security"
            className="mt-3 inline-flex min-h-11 items-center rounded text-sm text-ember hover:underline"
          >
            Manage sign-in security
          </Link>
        </section>
        <ChangePasswordForm key={`${user.id}:${user.role}`} actorId={user.id} />
      </div>
    </section>
  );
}
