import { z } from 'zod'
import { ANALYSIS_MODES, REVIEW_DEPTHS, type Preferences } from '../../shared/types'

export const PREFS_DEFAULTS: Preferences = {
  x: -1,
  y: -1,
  mode: 'general',
  reviewDepth: 'focused',
  privacyNoticeDismissed: false,
  startPaused: false
}

// Each field falls back independently so one corrupt value cannot wipe the rest.
const PrefsSchema = z
  .object({
    x: z.number().int().catch(PREFS_DEFAULTS.x),
    y: z.number().int().catch(PREFS_DEFAULTS.y),
    mode: z.enum(ANALYSIS_MODES).catch(PREFS_DEFAULTS.mode),
    reviewDepth: z.enum(REVIEW_DEPTHS).catch(PREFS_DEFAULTS.reviewDepth),
    privacyNoticeDismissed: z.boolean().catch(PREFS_DEFAULTS.privacyNoticeDismissed),
    startPaused: z.boolean().catch(PREFS_DEFAULTS.startPaused)
  })
  .catch(PREFS_DEFAULTS)

export function parsePrefs(raw: unknown): Preferences {
  return PrefsSchema.parse(raw ?? {})
}

/** The only preference fields the renderer is allowed to change over IPC. */
export const PrefsUpdateSchema = z
  .object({
    mode: z.enum(ANALYSIS_MODES).optional(),
    reviewDepth: z.enum(REVIEW_DEPTHS).optional(),
    privacyNoticeDismissed: z.boolean().optional(),
    startPaused: z.boolean().optional()
  })
  .strict()

export type PrefsUpdate = z.infer<typeof PrefsUpdateSchema>
