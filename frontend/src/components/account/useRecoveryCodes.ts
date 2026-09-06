import { useEffect, useRef, useState } from 'react';
import { generateRecoveryCodes, startRecoveryChallenge } from '@/lib/api/accountSecurity';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useAuthStore } from '@/stores/auth';
import { useAccountRequest } from './useAccountRequest';

export function useRecoveryCodes(methods: readonly string[], onChanged: () => Promise<void>) {
  const actor = useAuthStore((state) => state.user?.id);
  const beginRequest = useAccountRequest();
  const mounted = useRef(true);
  const [open, setOpen] = useState(false);
  const [method, setMethod] = useState<'authenticator' | 'email'>(
    methods.includes('authenticator') ? 'authenticator' : 'email',
  );
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [challenge, setChallenge] = useState<string | null>(null);
  const [codes, setCodes] = useState<string[]>([]);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const current = () => mounted.current && useAuthStore.getState().user?.id === actor;
  const action = useAsyncAction(async () => {
    const signal = beginRequest();
    if (method === 'email' && challenge === null) {
      const result = await startRecoveryChallenge(password, signal);
      if (current() && !signal.aborted) setChallenge(result.challenge_token);
      return;
    }
    const result = await generateRecoveryCodes(
      {
        password,
        method,
        code,
        challenge_token: challenge,
      },
      signal,
    );
    if (!current() || signal.aborted) return;
    setCodes(result.codes);
    setPassword('');
    setCode('');
    setChallenge(null);
    setOpen(false);
    await onChanged();
  });
  const reset = () => {
    setOpen(false);
    setPassword('');
    setCode('');
    setChallenge(null);
    action.clearError();
  };
  const changeMethod = (value: 'authenticator' | 'email') => {
    setMethod(value);
    setCode('');
    setChallenge(null);
    action.clearError();
  };
  return {
    open,
    setOpen,
    method,
    changeMethod,
    password,
    setPassword,
    code,
    setCode,
    challenge,
    setChallenge,
    codes,
    setCodes,
    action,
    reset,
  };
}
