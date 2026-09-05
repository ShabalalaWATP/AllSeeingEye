import { z } from 'zod';

export const countrySchema = z.object({
  iso2: z.string().length(2),
  iso3: z.string(),
  name: z.string(),
  /** west, south, east, north */
  bounds: z.tuple([z.number(), z.number(), z.number(), z.number()]),
  /** lon, lat */
  centroid: z.tuple([z.number(), z.number()]),
});
export type Country = z.infer<typeof countrySchema>;

export const countriesResponseSchema = z.object({ items: z.array(countrySchema) });
