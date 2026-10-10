import * as z from 'zod/mini';

/** Shared transport errors do not depend on account or administration schemas. */
export const errorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    request_id: z.optional(z.string().check(z.regex(/^[A-Za-z0-9-]{8,64}$/))),
    fields: z.optional(z.record(z.string(), z.string())),
  }),
});
export type ErrorEnvelope = z.infer<typeof errorEnvelopeSchema>;
