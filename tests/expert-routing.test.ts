import { describe, expect, it } from 'vitest'
import { evidenceForSelection, selectExperts } from '../src/main/agents/routing'
import type { Observation } from '../src/main/agents/schemas'
import type { RoutingSignalId } from '../src/shared/types'

function observation(signals: RoutingSignalId[]): Observation {
  return {
    materialType: 'proposal',
    subjectSummary: 'A proposal supplied for review.',
    evidence: signals.map((signalId, index) => ({
      id: `e${index + 1}`,
      text: signalId.replace(/_/g, ' '),
      location: 'body',
      confidence: 0.94
    })),
    limitations: [],
    signals: signals.map((signalId, index) => ({
      signalId,
      evidenceIds: [`e${index + 1}`],
      confidence: 0.94
    }))
  }
}

function ids(value: ReturnType<typeof selectExperts>): string[] {
  return value.map((item) => item.expertId)
}

describe('deterministic expert routing', () => {
  it('routes an ordinary priced business proposal without Cyber or Architecture', () => {
    const selected = ids(selectExperts(observation([
      'audience_facing_prose',
      'claim_or_argument',
      'product_or_service_proposal',
      'market_or_competitor_claim',
      'pricing_revenue_forecast_or_funding'
    ]), 'text', 'combined', 'general', 'Is this viable?'))
    expect(selected).toContain('product_uniqueness')
    expect(selected).toContain('finance_commercial')
    expect(selected).not.toContain('cyber_security_privacy')
    expect(selected).not.toContain('technical_architecture')
    expect(selected).not.toContain('writing_editorial')
  })

  it('does not let the security lens create security relevance', () => {
    const selected = ids(selectExperts(
      observation(['product_or_service_proposal']),
      'text', 'combined', 'security', ''
    ))
    expect(selected).toEqual(['product_uniqueness'])
  })

  it('routes concrete identity and API boundaries to Security and Architecture', () => {
    const selected = ids(selectExperts(observation([
      'identity_credentials_or_permissions',
      'api_upload_webhook_or_agent_tool'
    ]), 'screen', 'combined', 'general', ''))
    expect(selected).toContain('cyber_security_privacy')
    expect(selected).toContain('technical_architecture')
  })

  it('routes an explicit UK English request to Writing', () => {
    const selected = selectExperts(
      observation(['audience_facing_prose']),
      'text', 'focused', 'general', 'Correct the grammar and use UK English.'
    )
    expect(selected[0].expertId).toBe('writing_editorial')
    expect(selected[0].explicitlyRequested).toBe(true)
  })

  it('suppresses automatic transcript surface review without editorial intent', () => {
    const selected = ids(selectExperts(observation([
      'audience_facing_prose',
      'concrete_editorial_risk',
      'product_or_service_proposal'
    ]), 'voice_transcript', 'combined', 'general', 'Analyse the idea.'))
    expect(selected).toContain('product_uniqueness')
    expect(selected).not.toContain('writing_editorial')
  })

  it('routes an evening cappuccino voice note to Health rather than a fallback', () => {
    const selected = ids(selectExperts(
      observation(['sleep_caffeine_or_fatigue']),
      'voice_transcript', 'focused', 'general', ''
    ))
    expect(selected).toEqual(['health_wellbeing'])
    expect(selected).not.toContain('evidence_research')
    expect(selected).not.toContain('ethics_societal')
  })

  it('keeps urgent health red flags mandatory in focused mode', () => {
    const selected = selectExperts(
      observation(['urgent_health_red_flag', 'product_or_service_proposal']),
      'voice_transcript', 'focused', 'strategy', 'Is this product differentiated?'
    )
    const health = selected.find((item) => item.expertId === 'health_wellbeing')
    expect(health?.mandatory).toBe(true)
  })

  it('does not treat an ordinary coffee-shop product proposal as health advice', () => {
    const selected = ids(selectExperts(
      observation(['product_or_service_proposal']),
      'text', 'combined', 'general', 'Review the loyalty app proposal.'
    ))
    expect(selected).toEqual(['product_uniqueness'])
    expect(selected).not.toContain('health_wellbeing')
  })

  it('preserves mandatory child and high-stakes routes in focused mode', () => {
    const selected = ids(selectExperts(observation([
      'children_or_vulnerable_people',
      'high_stakes_automated_decision',
      'product_or_service_proposal'
    ]), 'text', 'focused', 'strategy', 'Is the product differentiated?'))
    expect(selected).toContain('legal_regulatory')
    expect(selected).toContain('ethics_societal')
    expect(selected).toContain('product_uniqueness')
  })

  it('uses the Evidence generalist instead of forcing an unrelated specialist', () => {
    const selected = selectExperts(observation(['claim_or_argument']), 'text', 'focused', 'general', '')
    expect(selected.map((item) => item.expertId)).toEqual(['evidence_research'])
    expect(selected[0].reason).toContain('No specialist threshold')
  })

  it('scopes each expert call to its selected evidence IDs', () => {
    const observed = observation([
      'pricing_revenue_forecast_or_funding',
      'security_incident_vulnerability_or_secret'
    ])
    const finance = selectExperts(observed, 'text', 'combined', 'general', '')
      .find((item) => item.expertId === 'finance_commercial')!
    expect(evidenceForSelection(observed, finance).map((item) => item.id)).toEqual(['e1'])
  })
})
