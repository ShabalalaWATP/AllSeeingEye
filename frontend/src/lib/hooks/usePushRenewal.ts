import { useEffect } from 'react';

import { pushSupported } from '@/lib/browserPush';
import { PUSH_CHANGED_MESSAGE, renewPush } from '@/lib/pushRenewal';

/** Re-register a replaced push subscription for the signed-in account, best effort. */
export function usePushRenewal(owner: string | null): void {
  useEffect(() => {
    if (owner === null || !pushSupported()) return;
    const renew = () => {
      void renewPush(owner).catch(() => {
        // The record is unchanged, so the next load or worker message tries again.
      });
    };
    const onMessage = (event: MessageEvent) => {
      if ((event.data as { type?: unknown } | null)?.type === PUSH_CHANGED_MESSAGE) renew();
    };
    const worker = navigator.serviceWorker;
    renew();
    worker.addEventListener('message', onMessage);
    return () => {
      worker.removeEventListener('message', onMessage);
    };
  }, [owner]);
}
