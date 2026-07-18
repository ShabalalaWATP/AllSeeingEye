import { describe, expect, it } from 'vitest'
import { MODE_ADDENDA, buildInstruction } from '../src/main/core/prompts'
import { ANALYSIS_MODES, type AnalysisMode } from '../src/shared/types'

describe('buildInstruction', () => {
  it('contains the rules block exactly once', () => {
    const text = buildInstruction('general', 'screen')
    expect(text.match(/Rules:/g)).toHaveLength(1)
  })

  it('appends the addendum for every mode', () => {
    for (const mode of ANALYSIS_MODES) {
      const text = buildInstruction(mode, 'screen')
      expect(text).toContain(`Mode focus: ${MODE_ADDENDA[mode]}`)
    }
  })

  it('falls back to general for an unknown mode', () => {
    const text = buildInstruction('nonsense' as AnalysisMode, 'screen')
    expect(text).toContain(`Mode focus: ${MODE_ADDENDA.general}`)
  })

  it('keeps the security mode defensive-only', () => {
    expect(buildInstruction('security', 'screen')).toContain(
      'Do not provide offensive exploitation steps.'
    )
  })

  it('scopes to the screenshot for screen analysis', () => {
    const text = buildInstruction('general', 'screen')
    expect(text).toContain('clearly visible in the supplied screenshot')
    expect(text).toContain('analysing a screenshot')
  })

  it('scopes to the message for text analysis and never mentions screenshots', () => {
    const text = buildInstruction('general', 'text')
    expect(text).toContain('material supplied in the message')
    expect(text).not.toContain('screenshot')
  })

  it('includes the no-issue rule', () => {
    expect(buildInstruction('general', 'screen')).toContain('hasMaterialIssue to false')
  })
})
