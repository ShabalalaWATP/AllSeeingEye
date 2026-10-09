import { useEffect, useState } from 'react';
import { z } from 'zod';

import type { components } from '@/lib/api/types.gen';

type Retention = Pick<components['schemas']['PublicSiteOut'], 'enterprise_enquiry_retention_days'>;
const schema: z.ZodType<Retention> = z.object({
  enterprise_enquiry_retention_days: z.number().int().min(30).max(3650),
});
type State = { status: 'loading' | 'unavailable' } | { status: 'ready'; days: number };

/** A failed public request must never turn the code default into a deployment claim. */
export function usePublicRetention(): State {
  const [state, setState] = useState<State>({ status: 'loading' });
  useEffect(() => {
    const controller = new AbortController();
    void fetch('/api/site', { credentials: 'omit', cache: 'no-store', signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('Public configuration unavailable');
        return schema.parse(await response.json());
      })
      .then((facts) => {
        if (!controller.signal.aborted)
          setState({ status: 'ready', days: facts.enterprise_enquiry_retention_days });
      })
      .catch(() => {
        if (!controller.signal.aborted) setState({ status: 'unavailable' });
      });
    return () => {
      controller.abort();
    };
  }, []);
  return state;
}
