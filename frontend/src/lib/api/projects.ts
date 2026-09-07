/** Source-reported project facts, with explicit unknown and year-only dates. */
import { z } from 'zod';

const boundedText = (limit: number) =>
  z.string().refine((value) => {
    const characters = Array.from(value);
    return (
      value.trim().length > 0 &&
      characters.length <= limit &&
      characters.every((char) => {
        const code = char.codePointAt(0) ?? 0;
        return code >= 32 && (code < 0xd800 || code > 0xdfff);
      })
    );
  }, 'Invalid or oversized project text');

const year = z.number().int().min(1).max(9998).nullable();

export const projectSchema = z.object({
  dataset_id: boundedText(120),
  release_id: boundedText(120),
  project_id: boundedText(120),
  source_sha256: z.string().regex(/^[a-f0-9]{64}$/),
  recipient_iso3: z.string().regex(/^[A-Z]{3}$/),
  reported_status: boundedText(300),
  precision: boundedText(100),
  attribution: boundedText(1000),
  data_licence: boundedText(300),
  geometry_licence: boundedText(300),
  limitations: boundedText(2000),
  commitment_year: year,
  implementation_year: year,
  completion_year: year,
});

export type ProjectMetadata = z.infer<typeof projectSchema>;
