/** The signed-in account's acceptance of the Terms and Acceptable Use Policy. */
import { z } from 'zod';

import { apiCall } from './client';
import type { components } from './types.gen';

export type TermsStatus = components['schemas']['TermsStatusOut'];

export const termsStatusSchema: z.ZodType<TermsStatus> = z.object({
  current_version: z.string(),
  accepted_version: z.string().nullable(),
  accepted_at: z.string().nullable(),
  acceptance_required: z.boolean(),
});

/** Accept exactly the version the reader was shown; the server refuses a superseded one. */
export function acceptTerms(version: string): Promise<TermsStatus> {
  return apiCall('/api/me/terms-acceptance', {
    method: 'POST',
    body: { version },
    schema: termsStatusSchema,
  });
}
