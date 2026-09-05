import { useState } from 'react';

import { confirmTotp, disableTotp, enrolTotp, fetchTotpStatus } from '@/lib/api/totp';
import type { TotpEnrolment } from '@/lib/api/totp';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useResource } from '@/lib/hooks/useResource';
import { useAuthStore } from '@/stores/auth';

export function useTotpSettings() {
  const resource = useResource(fetchTotpStatus);
  const [enrolment, setEnrolment] = useState<TotpEnrolment | null>(null);
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const action = useAsyncAction(async () => {
    if (resource.data?.enabled) {
      await disableTotp(password, code);
    } else if (enrolment !== null) {
      await confirmTotp(code);
    } else {
      const result = await enrolTotp(password);
      setPassword('');
      setEnrolment(result);
      return;
    }
    setPassword('');
    setCode('');
    setEnrolment(null);
    // Changes revoke all refresh sessions. Return to login immediately so the next
    // session reflects the configured factor, including the current browser.
    useAuthStore.getState().clearSession();
  });
  const restart = () => {
    setEnrolment(null);
    setCode('');
    action.clearError();
  };
  return { resource, enrolment, password, setPassword, code, setCode, action, restart };
}
