import { z } from 'zod';
import type { components } from './types.gen';

export type RegistryIdentifier = components['schemas']['RegistryIdentifierIn'];
export type RegistryLookup = components['schemas']['RegistryLookup'];
export const registryLabels = {
  lei: 'LEI',
  sec_cik: 'SEC CIK',
  gb_company_number: 'UK company number',
} satisfies Record<RegistryIdentifier['namespace'], string>;
export const registryNamespaceSchema = z.enum(['lei', 'sec_cik', 'gb_company_number']);
export const registryIdentifierSchema = z.object({
  id: z.string().min(1).max(64),
  namespace: registryNamespaceSchema,
  value: z.string().min(1).max(300),
}) satisfies z.ZodType<RegistryIdentifier>;
export const registryLookupSchema = z.object({
  candidate_id: z.string(),
  identifier_id: z.string(),
  namespace: registryNamespaceSchema,
  original_value: z.string(),
  subject: z.string(),
}) satisfies z.ZodType<RegistryLookup>;
