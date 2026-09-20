import { z } from 'zod';

/** Frozen geometry returned by the server, including its canonical content hash. */
export const frozenAreaSchema = z.object({
  geometry: z.record(z.string(), z.unknown()),
  sha256: z.string().regex(/^[a-f0-9]{64}$/),
});
