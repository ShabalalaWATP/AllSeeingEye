import { describe, expect, it } from 'vitest'
import {
  ExpertAnalysisSchema,
  ObservationSchema,
  buildReport,
  primaryFinding,
  sanitiseExpertAnalysis,
  sanitiseSynthesis,
  type ObservationRoute
} from '../src/main/agents/schemas'
import type { ExpertAnalysis, ExpertFinding } from '../src/shared/types'

const route: ObservationRoute = {
  materialType: 'architecture proposal',
  subjectSummary: 'A multi-tenant service with shared administration.',
  evidence: [{ id: 'e1', text: 'shared administrator', location: 'diagram', confidence: 0.9 }],
  limitations: [],
  signals: [{
    signalId: 'identity_credentials_or_permissions',
    evidenceIds: ['e1'],
    confidence: 0.9
  }],
  selectedExperts: [
    {
      expertId: 'cyber_security_privacy', reason: 'Shared privilege boundary.', relevance: 0.9,
      evidenceIds: ['e1'], signalIds: ['identity_credentials_or_permissions'],
      explicitlyRequested: false, mandatory: false
    },
    {
      expertId: 'technical_architecture', reason: 'Multi-tenant service design.', relevance: 0.86,
      evidenceIds: ['e1'], signalIds: ['identity_credentials_or_permissions'],
      explicitlyRequested: false, mandatory: false
    }
  ]
}

const finding: ExpertFinding = {
  expertId: 'cyber_security_privacy',
  evidenceIds: ['e1'],
  hasMaterialIssue: true,
  category: 'security',
  severity: 'high',
  headline: 'Shared administration creates an uncontrolled tenant-wide blast radius.',
  explanation: 'The evidence shows no isolation boundary for privileged actions.',
  visibleEvidence: 'e1: shared administrator',
  recommendation: 'Separate tenant privileges and test object/action authorisation.',
  confidence: 0.82,
  evidenceStrength: 'moderate',
  validationNeeded: 'Run cross-tenant authorisation tests for every privileged action.',
  sourceRefs: ['sec.owasp.asvs5', 'invented.source']
}

function analysis(overrides: Partial<ExpertAnalysis> = {}): ExpertAnalysis {
  return {
    expertId: 'cyber_security_privacy',
    packVersion: 'wrong-version',
    applicability: 'relevant',
    summary: 'Material privilege-boundary concern.',
    findings: [finding],
    assumptions: [],
    questions: [],
    disclaimer: 'wrong disclaimer',
    ...overrides
  }
}

describe('ObservationSchema', () => {
  it('accepts a bounded evidence envelope and typed signals', () => {
    const { selectedExperts: _selectedExperts, ...observation } = route
    expect(ObservationSchema.parse(observation)).toEqual(observation)
  })

  it('rejects duplicate evidence IDs and unknown signal evidence', () => {
    const { selectedExperts: _selectedExperts, ...observation } = route
    expect(() => ObservationSchema.parse({
      ...observation,
      evidence: [...observation.evidence, observation.evidence[0]]
    })).toThrow()
    expect(() => ObservationSchema.parse({
      ...observation,
      signals: [{ ...observation.signals[0], evidenceIds: ['e2'] }]
    })).toThrow()
  })
})

describe('expert result sanitising', () => {
  it('pins identity/version/disclaimer and removes fabricated source IDs', () => {
    const clean = sanitiseExpertAnalysis(analysis(), 'cyber_security_privacy', route.evidence)
    expect(clean.expertId).toBe('cyber_security_privacy')
    expect(clean.packVersion).toBe('2026.07.18')
    expect(clean.findings[0].sourceRefs).toEqual(['sec.owasp.asvs5'])
    expect(clean.disclaimer).toContain('Defensive issue-spotting')
  })

  it('drops findings that cite no valid observation evidence', () => {
    const clean = sanitiseExpertAnalysis(
      analysis({ findings: [{ ...finding, evidenceIds: ['e9'] }] }),
      'cyber_security_privacy',
      route.evidence
    )
    expect(clean.findings).toEqual([])
  })

  it('rejects findings from an expert that abstains', () => {
    expect(() => ExpertAnalysisSchema.parse(analysis({ applicability: 'not_relevant' }))).toThrow()
  })

  it('normalises a no-issue synthesis to low severity', () => {
    const clean = sanitiseSynthesis({
      ...finding,
      hasMaterialIssue: false,
      severity: 'critical',
      agreements: [],
      disagreements: [],
      prioritisedActions: []
    })
    expect(clean.severity).toBe('low')
  })

  it('preserves allow-listed health sources and removes fabricated ones', () => {
    const healthFinding: ExpertFinding = {
      ...finding,
      expertId: 'health_wellbeing',
      category: 'health',
      severity: 'low',
      sourceRefs: ['health.nhs.insomnia', 'invented.health.source']
    }
    const clean = sanitiseExpertAnalysis(analysis({
      expertId: 'health_wellbeing',
      findings: [healthFinding]
    }), 'health_wellbeing', route.evidence)
    expect(clean.findings[0].category).toBe('health')
    expect(clean.findings[0].sourceRefs).toEqual(['health.nhs.insomnia'])
  })
})

describe('report projection', () => {
  it('hides routed experts that abstained as not relevant', () => {
    const architecture = analysis({
      expertId: 'technical_architecture',
      applicability: 'not_relevant',
      findings: []
    })
    const report = buildReport('run-1', route, 'combined', '', [analysis(), architecture], null)
    expect(report.selectedExperts.map((item) => item.expertId)).toEqual([
      'cyber_security_privacy'
    ])
  })

  it('projects the highest-severity specialist finding without synthesis', () => {
    const low = analysis({
      expertId: 'technical_architecture',
      findings: [{ ...finding, expertId: 'technical_architecture', severity: 'low' }]
    })
    const report = buildReport('run-2', route, 'combined', '', [analysis(), low], null)
    expect(primaryFinding(report).severity).toBe('high')
  })
})
