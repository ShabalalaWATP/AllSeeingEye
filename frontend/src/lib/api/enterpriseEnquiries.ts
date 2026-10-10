import * as z from 'zod/mini';

import { apiCall } from './client';
import type { components } from './types.gen';

export type EnterpriseEnquiryInput = components['schemas']['EnquiryIn'];
const confirmation: z.ZodMiniType<components['schemas']['MessageOut']> = z.object({
  message: z.string(),
});

/** Public admission never attaches a bearer token or retries through session refresh. */
export async function submitEnterpriseEnquiry(
  body: EnterpriseEnquiryInput,
  signal: AbortSignal,
): Promise<void> {
  await apiCall('/api/enquiries', {
    method: 'POST',
    body,
    signal,
    auth: false,
    schema: confirmation,
  });
}
