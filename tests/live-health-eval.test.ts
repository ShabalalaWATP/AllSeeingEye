import { describe, expect, it } from 'vitest'
import { evidenceForSelection } from '../src/main/agents/routing'
import { observeAndRoute, runExpert } from '../src/main/openai-client'

const live = process.env.RUN_LIVE_MODEL_EVAL === '1' && Boolean(process.env.OPENAI_API_KEY)

describe.runIf(live)('live health model evaluation', () => {
  it('flags the sleep risk in an 8pm caffeinated cappuccino voice note', async () => {
    const route = await observeAndRoute(
      'voice_transcript',
      'Should I have a caffeinated cappuccino at 8pm if I want to sleep tonight?',
      'general',
      'focused',
      ''
    )
    const selection = route.selectedExperts.find((item) => item.expertId === 'health_wellbeing')
    expect(selection).toBeDefined()
    const analysis = await runExpert(
      'health_wellbeing',
      evidenceForSelection(route, selection!),
      `${route.materialType}. ${selection!.reason}`,
      route.limitations,
      '',
      'general',
      'voice_transcript'
    )
    expect(analysis.applicability).toBe('relevant')
    expect(analysis.findings.some((finding) =>
      finding.hasMaterialIssue && /sleep/i.test(`${finding.headline} ${finding.explanation}`)
    )).toBe(true)
    expect(analysis.findings.flatMap((finding) => finding.sourceRefs).some((id) =>
      id === 'health.nhs.insomnia' || id === 'health.efsa.caffeine'
    )).toBe(true)
  }, 120_000)
})
