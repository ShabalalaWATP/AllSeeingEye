import { z } from 'zod'
import {
  ALLOWED_VOICE_MIME_TYPES,
  ANALYSIS_MODES,
  MAX_FOCUS_QUESTION_LENGTH,
  MAX_VOICE_BYTES,
  MAX_VOICE_SECONDS,
  REVIEW_DEPTHS
} from '../../shared/types'

export const VoiceAnalysisRequestSchema = z.object({
  sessionId: z.string().uuid(),
  bytes: z.instanceof(ArrayBuffer).refine(
    (value) => value.byteLength > 0 && value.byteLength <= MAX_VOICE_BYTES
  ),
  mimeType: z.enum(ALLOWED_VOICE_MIME_TYPES),
  durationMs: z.number().int().min(500).max(MAX_VOICE_SECONDS * 1_000),
  mode: z.enum(ANALYSIS_MODES),
  focusQuestion: z.string().max(MAX_FOCUS_QUESTION_LENGTH).optional(),
  depth: z.enum(REVIEW_DEPTHS).optional()
}).strict()
