/**
 * Route guards. RequireAuth waits for the session bootstrap, then either renders
 * the protected outlet or redirects to /login remembering the intended path.
 * RequireAdmin adds the role check. Authorisation is also enforced server-side;
 * these guards only shape navigation.
 */
import { Link, Navigate, Outlet, useLocation } from 'react-router';

import { Alert } from '@/components/ui/Alert';
import { LoadingScreen } from '@/components/ui/LoadingScreen';
import { selectIsAdmin, useAuthStore } from '@/stores/auth';

export function RequireAuth() {
  const status = useAuthStore((state) => state.status);
  const location = useLocation();

  if (status === 'unknown') {
    return <LoadingScreen label="Checking your session" />;
  }
  if (status === 'anonymous') {
    const from = `${location.pathname}${location.search}`;
    return <Navigate to="/login" replace state={{ from }} />;
  }
  return <Outlet />;
}

export function RequireAdmin() {
  const isAdmin = useAuthStore(selectIsAdmin);
  if (!isAdmin) {
    return (
      <div className="p-6">
        <Alert tone="warning" title="Admin access required">
          Your account does not have permission to view this page.
        </Alert>
        <Link
          to="/"
          className="mt-4 inline-flex min-h-11 items-center text-sm text-ember underline"
        >
          Return to research
        </Link>
      </div>
    );
  }
  return <Outlet />;
}

/** Redirects legacy link paths (/activate, /reset-password) keeping the query string. */
export function RedirectWithQuery({ to }: { to: string }) {
  const { search } = useLocation();
  return <Navigate to={{ pathname: to, search }} replace />;
}
