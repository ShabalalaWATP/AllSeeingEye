import { describe, expect, it } from 'vitest'
import {
  LIMITS,
  RedTeamFindingSchema,
  sanitiseFinding,
  truncate
} from '../src/main/core/finding-schema'
import type { RedTeamFinding } from '../src/shared/types'

const valid: RedTeamFinding = {
  hasMaterialIssue: true,
  category: 'assumption',
  severity: 'medium',
  headline: 'The proposal depends on accurate metadata but defines no validation mechanism.',
  explanation: 'The plan assumes clean inputs.',
  visibleEvidence: '"metadata is accurate"',
  recommendation: 'Define a validation step.',
  confidence: 0.8
}

describe('RedTeamFindingSchema', () => {
  it('accepts a valid finding', () => {
    expect(RedTeamFindingSchema.parse(valid)).toEqual(valid)
  })

  it('rejects an unknown category', () => {
    expect(() => RedTeamFindingSchema.parse({ ...valid, category: 'vibes' })).toThrow()
  })

  it('rejects an unknown severity', () => {
    expect(() => RedTeamFindingSchema.parse({ ...valid, severity: 'catastrophic' })).toThrow()
  })

  it('rejects extra keys (strict)', () => {
    expect(() => RedTeamFindingSchema.parse({ ...valid, extra: true })).toThrow()
  })

  it('rejects out-of-range confidence', () => {
    expect(() => RedTeamFindingSchema.parse({ ...valid, confidence: 1.4 })).toThrow()
    expect(() => RedTeamFindingSchema.parse({ ...valid, confidence: -0.1 })).toThrow()
  })
})

describe('sanitiseFinding', () => {
  it('truncates an over-long headline to the cap with an ellipsis', () => {
    const long = { ...valid, headline: 'x'.repeat(300) }
    const out = sanitiseFinding(long)
    expect(out.headline.length).toBeLessThanOrEqual(LIMITS.headline)
    expect(out.headline.endsWith('…')).toBe(true)
  })

  it('clamps confidence into [0, 1]', () => {
    expect(sanitiseFinding({ ...valid, confidence: 1.4 }).confidence).toBe(1)
    expect(sanitiseFinding({ ...valid, confidence: -0.2 }).confidence).toBe(0)
  })

  it('forces low severity when there is no material issue', () => {
    const out = sanitiseFinding({ ...valid, hasMaterialIssue: false, severity: 'high' })
    expect(out.severity).toBe('low')
  })

  it('leaves a compliant finding untouched', () => {
    expect(sanitiseFinding(valid)).toEqual(valid)
  })
})

describe('truncate', () => {
  it('returns short strings unchanged', () => {
    expect(truncate('short', 10)).toBe('short')
  })

  it('never exceeds the cap', () => {
    expect(truncate('abcdefghij', 5).length).toBeLessThanOrEqual(5)
  })
})
