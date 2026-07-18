import { z } from 'zod'
import {
  CATEGORIES,
  EVIDENCE_STRENGTHS,
  EXPERT_IDS,
  ROUTING_SIGNAL_IDS,
  SEVERITIES,
  type AnalysisReport,
  type CombinedSynthesis,
  type ExpertAnalysis,
  type ExpertFinding,
  type ExpertId,
  type RedTeamFinding,
  type ReviewDepth,
  type RoutingSignalId
} from '../../shared/types'
import { LIMITS, sanitiseFinding, truncate } from '../core/finding-schema'
import { getKnowledgePack } from '../knowledge/packs'

const short = (max: number): z.ZodString => z.string().max(max)

export const EvidenceItemSchema = z.object({
  id: z.string().regex(/^e[1-9][0-9]?$/),
  text: short(500),
  location: short(120),
  confidence: z.number().min(0).max(1)
}).strict()

export type EvidenceItem = z.infer<typeof EvidenceItemSchema>

export const ObservedSignalSchema = z.object({
  signalId: z.enum(ROUTING_SIGNAL_IDS),
  evidenceIds: z.array(z.string().regex(/^e[1-9][0-9]?$/)).min(1).max(6),
  confidence: z.number().min(0).max(1)
}).strict()

export interface ObservedSignal {
  signalId: RoutingSignalId
  evidenceIds: string[]
  confidence: number
}

export const ObservationSchema = z.object({
  materialType: short(100),
  subjectSummary: short(600),
  evidence: z.array(EvidenceItemSchema).min(1).max(14),
  limitations: z.array(short(240)).max(5),
  signals: z.array(ObservedSignalSchema).max(20)
}).strict().superRefine((value, ctx) => {
  const evidenceIds = value.evidence.map((item) => item.id)
  if (new Set(evidenceIds).size !== evidenceIds.length) {
    ctx.addIssue({ code: 'custom', path: ['evidence'], message: 'Evidence IDs must be unique' })
  }
  const known = new Set(evidenceIds)
  for (const [index, signal] of value.signals.entries()) {
    if (new Set(signal.evidenceIds).size !== signal.evidenceIds.length) {
      ctx.addIssue({ code: 'custom', path: ['signals', index, 'evidenceIds'], message: 'Signal evidence IDs must be unique' })
    }
    if (signal.evidenceIds.some((id) => !known.has(id))) {
      ctx.addIssue({ code: 'custom', path: ['signals', index, 'evidenceIds'], message: 'Signal references unknown evidence' })
    }
  }
})

export type Observation = z.infer<typeof ObservationSchema>
export type ObservationRoute = Observation & {
  selectedExperts: AnalysisReport['selectedExperts']
}

export const ExpertFindingSchema = z.object({
  expertId: z.enum(EXPERT_IDS),
  evidenceIds: z.array(z.string().regex(/^e[1-9][0-9]?$/)).min(1).max(4),
  hasMaterialIssue: z.boolean(),
  category: z.enum(CATEGORIES),
  severity: z.enum(SEVERITIES),
  headline: short(LIMITS.headline),
  explanation: short(LIMITS.explanation),
  visibleEvidence: short(LIMITS.visibleEvidence),
  recommendation: short(LIMITS.recommendation),
  confidence: z.number().min(0).max(1),
  evidenceStrength: z.enum(EVIDENCE_STRENGTHS),
  validationNeeded: short(400),
  sourceRefs: z.array(short(80)).max(6)
}).strict()

export const ExpertAnalysisSchema = z.object({
  expertId: z.enum(EXPERT_IDS),
  packVersion: short(40),
  applicability: z.enum(['relevant', 'not_relevant', 'insufficient_context']),
  summary: short(600),
  findings: z.array(ExpertFindingSchema).max(3),
  assumptions: z.array(short(240)).max(5),
  questions: z.array(short(240)).max(3),
  disclaimer: short(320)
}).strict().superRefine((value, ctx) => {
  if (value.applicability !== 'relevant' && value.findings.length > 0) {
    ctx.addIssue({
      code: 'custom',
      path: ['findings'],
      message: 'An abstaining expert cannot return findings'
    })
  }
})

export const CombinedSynthesisSchema = z.object({
  hasMaterialIssue: z.boolean(),
  category: z.enum(CATEGORIES),
  severity: z.enum(SEVERITIES),
  headline: short(LIMITS.headline),
  explanation: short(LIMITS.explanation),
  visibleEvidence: short(LIMITS.visibleEvidence),
  recommendation: short(LIMITS.recommendation),
  confidence: z.number().min(0).max(1),
  agreements: z.array(short(320)).max(4),
  disagreements: z.array(short(320)).max(4),
  prioritisedActions: z.array(short(320)).max(5)
}).strict()

function sanitiseExpertFinding(
  finding: ExpertFinding,
  expected: ExpertId,
  evidence: EvidenceItem[]
): ExpertFinding {
  const base = sanitiseFinding(finding)
  const allowedSources = new Set(getKnowledgePack(expected).sources.map((item) => item.id))
  const evidenceMap = new Map(evidence.map((item) => [item.id, item.text]))
  const evidenceIds = finding.evidenceIds.filter((id) => evidenceMap.has(id)).slice(0, 4)
  return {
    ...base,
    expertId: expected,
    evidenceIds,
    visibleEvidence: evidenceIds
      .map((id) => `${id}: ${evidenceMap.get(id)}`)
      .join(' · '),
    evidenceStrength: finding.evidenceStrength,
    validationNeeded: truncate(finding.validationNeeded, 400),
    sourceRefs: finding.sourceRefs.filter((id) => allowedSources.has(id)).slice(0, 6)
  }
}

export function sanitiseExpertAnalysis(
  analysis: ExpertAnalysis,
  expected: ExpertId,
  evidence: EvidenceItem[]
): ExpertAnalysis {
  const pack = getKnowledgePack(expected)
  return {
    expertId: expected,
    packVersion: pack.version,
    applicability: analysis.applicability,
    summary: truncate(analysis.summary, 600),
    findings: analysis.findings
      .slice(0, 3)
      .map((finding) => sanitiseExpertFinding(finding, expected, evidence))
      .filter((finding) => finding.evidenceIds.length > 0),
    assumptions: analysis.assumptions.map((item) => truncate(item, 240)).slice(0, 5),
    questions: analysis.questions.map((item) => truncate(item, 240)).slice(0, 3),
    disclaimer: pack.disclaimer
  }
}

export function sanitiseSynthesis(value: CombinedSynthesis): CombinedSynthesis {
  return {
    ...sanitiseFinding(value),
    agreements: value.agreements.map((item) => truncate(item, 320)).slice(0, 4),
    disagreements: value.disagreements.map((item) => truncate(item, 320)).slice(0, 4),
    prioritisedActions: value.prioritisedActions.map((item) => truncate(item, 320)).slice(0, 5)
  }
}

const severityRank = { low: 0, medium: 1, high: 2, critical: 3 } as const

export function primaryFinding(report: AnalysisReport): RedTeamFinding {
  if (report.synthesis) return report.synthesis
  const findings = report.expertAnalyses.flatMap((analysis) => analysis.findings)
  const material = findings.filter((finding) => finding.hasMaterialIssue)
  if (material.length > 0) {
    return [...material].sort((a, b) =>
      severityRank[b.severity] - severityRank[a.severity] || b.confidence - a.confidence
    )[0]
  }
  return {
    hasMaterialIssue: false,
    category: 'other',
    severity: 'low',
    headline: 'No material issue was found within the selected expert scope.',
    explanation: 'The selected experts found no material weakness in the evidence available.',
    visibleEvidence: '',
    recommendation: 'Review the listed assumptions and unanswered questions before relying on this result.',
    confidence: 0.6
  }
}

export function buildReport(
  runId: string,
  route: ObservationRoute,
  depth: ReviewDepth,
  focusQuestion: string,
  analyses: ExpertAnalysis[],
  synthesis: CombinedSynthesis | null
): AnalysisReport {
  const selectionMap = new Map(route.selectedExperts.map((item) => [item.expertId, item]))
  const contributors = new Set(analyses.filter((analysis) => {
    if (analysis.applicability === 'relevant') return true
    if (analysis.applicability === 'not_relevant') return false
    const selection = selectionMap.get(analysis.expertId)
    return Boolean(selection?.explicitlyRequested || selection?.mandatory)
  }).map((analysis) => analysis.expertId))
  return {
    runId,
    depth,
    focusQuestion,
    subjectSummary: route.subjectSummary,
    selectedExperts: route.selectedExperts.filter((selection) => contributors.has(selection.expertId)),
    expertAnalyses: analyses.filter((analysis) => contributors.has(analysis.expertId)),
    synthesis
  }
}
