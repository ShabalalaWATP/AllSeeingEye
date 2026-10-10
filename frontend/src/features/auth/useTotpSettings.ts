import { useCallback, useEffect, useState } from 'react';

import { isApiError } from '@/lib/api/errors';
import { confirmEmailMfa, fetchMfaStatus, startEmailMfa } from '@/lib/api/mfa';
import { confirmTotp, disableTotp, enrolTotp } from '@/lib/api/totp';
import type { TotpEnrolment } from '@/lib/api/totp';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useResource } from '@/lib/hooks/useResource';
import { useAuthStore } from '@/stores/auth';

type Method = 'authenticator' | 'email';
export function useTotpSettings() {
  const resource = useResource(fetchMfaStatus);
  const generation = useAuthStore((state) => state.sessionGeneration);
  const [method, setMethod] = useState<Method | null>(null);
  const [enrolment, setEnrolment] = useState<TotpEnrolment | null>(null);
  const [challenge, setChallenge] = useState<string | null>(null);
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const reset = useCallback(() => {
    setMethod(null);
    setPassword('');
    setEnrolment(null);
    setChallenge(null);
    setCode('');
  }, []);
  const enabled = method !== null && (resource.data?.methods.includes(method) ?? false);
  const action = useAsyncAction(async () => {
    try {
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
      if (useAuthStore.getState().sessionGeneration === generation) {
        useAuthStore.getState().clearSession();
      }
    } catch (error) {
      // The generation subscription already cleared the previous login's proofs.
      if (!isApiError(error) || error.code !== 'session_changed') throw error;
    }
  });
  const { clearError } = action;
  useEffect(
    () =>
      useAuthStore.subscribe((current, previous) => {
        if (current.sessionGeneration !== previous.sessionGeneration) {
          reset();
          clearError();
        }
      }),
    [clearError, reset],
  );
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
