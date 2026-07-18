import { z } from 'zod'
import { CATEGORIES, SEVERITIES, type RedTeamFinding } from '../../shared/types'

export const LIMITS = {
  headline: 180,
  explanation: 800,
  visibleEvidence: 400,
  recommendation: 800
} as const

export const RedTeamFindingSchema = z
  .object({
    hasMaterialIssue: z.boolean(),
    category: z.enum(CATEGORIES),
    severity: z.enum(SEVERITIES),
    headline: z.string().max(LIMITS.headline),
    explanation: z.string().max(LIMITS.explanation),
    visibleEvidence: z.string().max(LIMITS.visibleEvidence),
    recommendation: z.string().max(LIMITS.recommendation),
    confidence: z.number().min(0).max(1)
  })
  .strict()

// Compile-time guard: the schema output must stay assignable to the shared type.
const _assignable: z.ZodType<RedTeamFinding> = RedTeamFindingSchema
void _assignable

export function truncate(value: string, max: number): string {
  return value.length <= max ? value : `${value.slice(0, Math.max(0, max - 1)).trimEnd()}…`
}

/**
 * Defence in depth over the structured output: enforce every length cap and
 * value range locally regardless of what the API validated, and normalise the
 * no-issue case to low severity.
 */
export function sanitiseFinding(finding: RedTeamFinding): RedTeamFinding {
  return {
    hasMaterialIssue: finding.hasMaterialIssue,
    category: finding.category,
    severity: finding.hasMaterialIssue ? finding.severity : 'low',
    headline: truncate(finding.headline, LIMITS.headline),
    explanation: truncate(finding.explanation, LIMITS.explanation),
    visibleEvidence: truncate(finding.visibleEvidence, LIMITS.visibleEvidence),
    recommendation: truncate(finding.recommendation, LIMITS.recommendation),
    confidence: Math.min(1, Math.max(0, finding.confidence))
  }
}
