import { Link } from 'react-router';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchMfaStatus } from '@/lib/api/mfa';
import { fetchRecoveryStatus } from '@/lib/api/accountSecurity';
import { describeError } from '@/lib/api/errors';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useAuthStore } from '@/stores/auth';
import { AccountSessions } from './AccountSessions';
import { RecoveryCodes } from './RecoveryCodes';

async function loadSecurity() {
  const [mfa, recovery] = await Promise.all([fetchMfaStatus(), fetchRecoveryStatus()]);
  return { mfa, recovery };
}
export function ProfileSecurity() {
  const actor = useAuthStore((state) => state.user?.id);
  return actor ? <SecurityContent key={actor} /> : null;
}
function SecurityContent() {
  const resource = useScopedResource(loadSecurity);
  return (
    <div className="flex flex-col gap-8">
      <section className="space-y-4" aria-labelledby="profile-mfa-title">
        <h2 id="profile-mfa-title" className="text-xl font-semibold">
          Sign-in protection
        </h2>
        {resource.loading && (
          <p role="status" className="text-sm text-muted">
            Loading account security...
          </p>
        )}
        {resource.error && (
          <>
            <Alert tone="error">{describeError(resource.error)}</Alert>
            <Button variant="secondary" onClick={() => void resource.reload()}>
              Retry security
            </Button>
          </>
        )}
        {resource.data && (
          <>
            <div className="flex flex-wrap gap-3 text-sm">
              <span className="rounded border border-line px-3 py-2">
                {resource.data.mfa.methods.length ? 'MFA enabled' : 'MFA not enabled'}
              </span>
              {resource.data.mfa.methods.includes('authenticator') && (
                <span className="py-2 text-muted">Authenticator app</span>
              )}
              {resource.data.mfa.methods.includes('email') && (
                <span className="py-2 text-muted">Email verification</span>
              )}
            </div>
            {resource.data.mfa.required && (
              <p className="text-sm text-muted">
                Administrators must keep at least one MFA method enabled.
              </p>
            )}
          </>
        )}
        <Link
          to="/account/security"
          className="inline-flex min-h-11 items-center text-sm text-ember hover:underline"
        >
          Manage MFA methods
        </Link>
      </section>
      {resource.data && (
        <RecoveryCodes
          status={resource.data.recovery}
          methods={resource.data.mfa.methods}
          onChanged={resource.reload}
        />
      )}
      <AccountSessions />
    </div>
  );
}
