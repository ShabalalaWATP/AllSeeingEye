import { z } from 'zod'

export const FullReviewRequestSchema = z.object({ runId: z.string().uuid() }).strict()
