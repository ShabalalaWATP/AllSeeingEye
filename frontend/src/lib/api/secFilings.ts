import { z } from 'zod';
import { apiCall, apiBlob } from './client';
import type { components } from './types.gen';
import { researchInputReceiptSchema } from './researchInputs';
import { scopedMutation } from '@/lib/workspaceAccess';
export type SecFilingsSearch = components['schemas']['SecFilingsSearchIn'];
export type SecFilingChoice = components['schemas']['SecFilingChoiceOut'];
export type SecFilingsPage = components['schemas']['SecFilingsPageOut'];
export const secFilingChoiceSchema = z.object({
  selection_id: z.uuid(),
  cik: z.string().regex(/^[0-9]{1,10}$/),
  accession: z.string().max(30),
  primary_document: z.string().max(200),
  form: z.string().max(40),
  filing_date: z.iso.date(),
  company_name: z.string().max(500),
  expires_at: z.iso.datetime({ offset: true }),
}) satisfies z.ZodType<SecFilingChoice>;
export const secFilingsPageSchema = z.object({
  items: z.array(secFilingChoiceSchema).max(20),
  archive_page: z.number().int().min(0).max(50),
  archive_pages: z.number().int().min(0).max(50),
  offset: z.number().int().min(0).max(9980),
  next_offset: z.number().int().min(0).max(9980).nullable(),
  limitations: z.array(z.string().max(2000)).max(30),
}) satisfies z.ZodType<SecFilingsPage>;
export function searchSecFilings(body: SecFilingsSearch, signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall('/api/research/sec/filings', {
      method: 'POST',
      body,
      signal,
      schema: secFilingsPageSchema,
    }),
  );
}
export function importSecFiling(id: string, signal: AbortSignal) {
  return scopedMutation(() =>
    apiCall(`/api/research/sec/filings/${encodeURIComponent(id)}/import`, {
      method: 'POST',
      signal,
      schema: researchInputReceiptSchema,
    }),
  );
}
export function downloadSecOriginal(id: string, signal: AbortSignal) {
  return scopedMutation(() =>
    apiBlob(`/api/research/sec/filings/${encodeURIComponent(id)}/original`, {
      signal,
      headers: { Accept: 'application/octet-stream' },
    }),
  );
}
