import { z } from 'zod';
import type { components } from './types.gen';

export const LICENCE_UNAVAILABLE = 'Not available on this installation due to licence terms';

export const sourceLicenceSchema = z.object({
  commercial_use: z.enum(['allowed', 'forbidden', 'licence_required']),
  attribution_required: z.boolean(),
  licence_ref: z.string(),
  available: z.boolean(),
  acknowledged: z.boolean(),
  reason: z.string(),
}) satisfies z.ZodType<components['schemas']['SourceLicenceOut']>;

export type SourceLicence = components['schemas']['SourceLicenceOut'];
