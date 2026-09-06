import { useState } from 'react';

import { confirmEmailMfa, fetchMfaStatus, startEmailMfa } from '@/lib/api/mfa';
import { confirmTotp, disableTotp, enrolTotp } from '@/lib/api/totp';
import type { TotpEnrolment } from '@/lib/api/totp';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useResource } from '@/lib/hooks/useResource';
import { useAuthStore } from '@/stores/auth';

type Method = 'authenticator' | 'email';
export function useTotpSettings() {
  const resource = useResource(fetchMfaStatus);
  const actorId = useAuthStore((state) => state.user?.id);
  const [method, setMethod] = useState<Method | null>(null);
  const [enrolment, setEnrolment] = useState<TotpEnrolment | null>(null);
  const [challenge, setChallenge] = useState<string | null>(null);
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const enabled = method !== null && (resource.data?.methods.includes(method) ?? false);
  const action = useAsyncAction(async () => {
    if (method === null) return;
    if (method === 'email') {
      const operation = enabled ? 'disable' : 'enrol';
      if (challenge === null) {
        const pending = await startEmailMfa(operation, password);
        setChallenge(pending.challenge_token);
        setPassword('');
        return;
      }
      await confirmEmailMfa(operation, challenge, code);
    } else if (enabled) {
      await disableTotp(password, code);
    } else if (enrolment !== null) {
      await confirmTotp(code);
    } else {
      const result = await enrolTotp(password);
      setPassword('');
      setEnrolment(result);
      return;
    }
    reset();
    // Factor changes revoke every session. Do not clear a replacement identity.
    if (useAuthStore.getState().user?.id === actorId) {
      useAuthStore.getState().clearSession();
    }
  });
  function reset() {
    setMethod(null);
    setPassword('');
    setEnrolment(null);
    setChallenge(null);
    setCode('');
  }
  const restart = () => {
    reset();
    action.clearError();
  };
  return {
    resource,
    method,
    setMethod,
    enabled,
    enrolment,
    challenge,
    password,
    setPassword,
    code,
    setCode,
    action,
    restart,
  };
}
