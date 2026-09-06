/**
 * Response schemas derived from docs/api/AUTH_API.md. Every response is validated
 * at the boundary before it reaches a store or a page. Types are inferred from
 * the schemas; once `openapi.json` is exported, `pnpm gen:api` produces
 * `types.gen.ts` and these can be checked against it or replaced.
 */
import { z } from 'zod';

export const roleSchema = z.enum(['user', 'manager', 'admin']);
export type Role = z.infer<typeof roleSchema>;

export const userSchema = z.object({
  id: z.string(),
  email: z.string(),
  display_name: z.string(),
  role: roleSchema,
  is_active: z.boolean(),
  created_at: z.string(),
  last_login_at: z.string().nullable(),
});
export type User = z.infer<typeof userSchema>;

export const accountRequestSchema = z.object({
  id: z.string(),
  email: z.string(),
  display_name: z.string(),
  reason: z.string().nullable(),
  status: z.enum(['pending', 'approved', 'rejected']),
  created_at: z.string(),
});
export type AccountRequest = z.infer<typeof accountRequestSchema>;

export const auditEntrySchema = z.object({
  id: z.number().int(),
  at: z.string(),
  actor_user_id: z.string().nullable(),
  action: z.string(),
  subject: z.string().nullable(),
  ip: z.string().nullable(),
  details: z.record(z.string(), z.unknown()),
});
export type AuditEntry = z.infer<typeof auditEntrySchema>;

export const tokenResponseSchema = z.object({
  access_token: z.string().min(1),
  token_type: z.literal('bearer'),
  expires_in: z.number().int(),
  user: userSchema,
});
export type TokenResponse = z.infer<typeof tokenResponseSchema>;

export const errorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    fields: z.record(z.string(), z.string()).optional(),
  }),
});
export type ErrorEnvelope = z.infer<typeof errorEnvelopeSchema>;

export const messageResponseSchema = z.object({ message: z.string() });

export const accountRequestListSchema = z.object({ items: z.array(accountRequestSchema) });
export const userListSchema = z.object({ items: z.array(userSchema) });

export const approveResponseSchema = z.object({
  user: userSchema,
  activation_link: z.string().nullable(),
  expires_at: z.string(),
});
export type ApproveResponse = z.infer<typeof approveResponseSchema>;

export const resetLinkResponseSchema = z.object({
  reset_link: z.string(),
  expires_at: z.string(),
});
export type ResetLinkResponse = z.infer<typeof resetLinkResponseSchema>;

export const auditPageSchema = z.object({
  items: z.array(auditEntrySchema),
  next_before: z.number().int().nullable(),
});
export type AuditPage = z.infer<typeof auditPageSchema>;
