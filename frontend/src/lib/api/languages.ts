import { z } from 'zod';

import { apiCall } from './client';
import type { components } from './types.gen';

export type LanguageCapability = components['schemas']['LanguageCapabilityOut'];
export type LanguageCatalogue = components['schemas']['LanguageCatalogueOut'];
const capabilitySchema: z.ZodType<LanguageCapability> = z.object({
  code: z.string(),
  label: z.string(),
  native_label: z.string(),
  direction: z.enum(['ltr', 'rtl']),
  report_supported: z.boolean(),
  pdf_supported: z.boolean(),
  detector_code: z.string().nullable(),
  google_news_edition: z.object({ hl: z.string(), gl: z.string(), ceid: z.string() }).nullable(),
});
const catalogueSchema: z.ZodType<LanguageCatalogue> = z.object({
  version: z.literal('1'),
  languages: z.array(capabilitySchema),
});
export const fetchLanguageCatalogue = () =>
  apiCall('/api/me/profile/languages', { schema: catalogueSchema });
