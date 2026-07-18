import { describe, expect, it } from 'vitest'
import { buildQuickInstruction } from '../src/main/core/quick-prompt'
import {
  QUICK_TAKE_MAX_LENGTH,
  QuickTakeSchema,
  sanitiseQuickTake
} from '../src/main/core/quick-take'

describe('QuickTakeSchema', () => {
  it('accepts exactly one concise answer field', () => {
    expect(QuickTakeSchema.parse({ answer: 'Use decaf if protecting tonight’s sleep.' }))
      .toEqual({ answer: 'Use decaf if protecting tonight’s sleep.' })
    expect(() => QuickTakeSchema.parse({ answer: 'Fine.', confidence: 0.8 })).toThrow()
  })

  it('rejects empty and over-long answers', () => {
    expect(() => QuickTakeSchema.parse({ answer: '' })).toThrow()
    expect(() => QuickTakeSchema.parse({ answer: 'x'.repeat(QUICK_TAKE_MAX_LENGTH + 1) }))
      .toThrow()
  })

  it('defensively trims and caps output', () => {
    expect(sanitiseQuickTake({ answer: '  A direct answer.  ' })).toBe('A direct answer.')
    expect(sanitiseQuickTake({ answer: 'x'.repeat(400) }).length)
      .toBeLessThanOrEqual(QUICK_TAKE_MAX_LENGTH)
  })
})

describe('buildQuickInstruction', () => {
  it.each(['screen', 'text', 'voice_transcript'] as const)(
    'keeps %s in the one-call quick-answer scope',
    (source) => {
      const prompt = buildQuickInstruction(source)
      expect(prompt).toContain('general model knowledge')
      expect(prompt).toContain('one or two short sentences')
      expect(prompt).toContain('Do not route to specialists')
      expect(prompt).not.toContain('sourceRefs')
      expect(prompt).not.toContain('selectedExperts')
    }
  )
})
