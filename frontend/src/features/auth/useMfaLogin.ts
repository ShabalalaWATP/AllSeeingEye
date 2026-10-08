import { useEffect, useRef, useState } from 'react';

import { enrolLoginApp, sendMfaEmail, verifyMfa } from '@/lib/api/mfa';
import type { MfaEnrolment, MfaMethod, PendingMfa } from '@/lib/api/mfa';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useAuthStore } from '@/stores/auth';

export function useMfaLogin(challenge: PendingMfa) {
  const mounted = useRef(true);
  const verification = useRef<AbortController | null>(null);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      verification.current?.abort();
    };
  }, []);
  const [method, setMethod] = useState<MfaMethod>(
    challenge.methods.includes('authenticator') ? 'authenticator' : 'email',
  );
  const [code, setCode] = useState('');
  const [emailSent, setEmailSent] = useState(challenge.email_sent);
  const [enrolment, setEnrolment] = useState<MfaEnrolment | null>(null);
  // Confirms the account address before a first authenticator is bound, when required.
  const [emailProof, setEmailProof] = useState('');
  const action = useAsyncAction(async (intent: 'verify' | 'email' | 'app') => {
    if (intent === 'email') {
      await sendMfaEmail(challenge.challenge_token);
      setEmailSent(true);
      setCode('');
      setEmailProof('');
    } else if (intent === 'app') {
      setEnrolment(
        await enrolLoginApp(
          challenge.challenge_token,
          challenge.authenticator_email_proof ? emailProof : undefined,
        ),
      );
      setEmailProof('');
    } else {
      const controller = new AbortController();
      verification.current = controller;
      const session = await verifyMfa(challenge.challenge_token, method, code, controller.signal);
      if (
        mounted.current &&
        !controller.signal.aborted &&
        useAuthStore.getState().status !== 'authenticated'
      ) {
        useAuthStore.getState().setSession(session);
      }
    }
  });
  const chooseMethod = (next: MfaMethod) => {
    setMethod(next);
    setCode('');
    action.clearError();
  };
  return {
    ...action,
    method,
    chooseMethod,
    code,
    setCode,
    emailSent,
    enrolment,
    emailProof,
    setEmailProof,
  };
}
