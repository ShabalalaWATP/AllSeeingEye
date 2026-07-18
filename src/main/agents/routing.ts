import {
  EXPERT_LABELS,
  ROUTING_SIGNAL_IDS,
  type AnalysisMode,
  type AnalysisSource,
  type ExpertId,
  type ExpertSelection,
  type ReviewDepth,
  type RoutingSignalId
} from '../../shared/types'
import type { Observation, ObservedSignal } from './schemas'

export const ROUTING_SIGNAL_DESCRIPTIONS: Record<RoutingSignalId, string> = {
  audience_facing_prose: 'substantial prose intended for a reader, such as a report, email, proposal, article or public message',
  explicit_language_review: 'an explicit request in the supplied work to edit grammar, spelling, clarity, tone or English',
  concrete_editorial_risk: 'an observable ambiguity, language defect or overclaim that could materially alter reader understanding',
  claim_or_argument: 'a conclusion, recommendation or contested factual claim that depends on reasoning or evidence',
  citations_statistics_or_research: 'citations, research, survey, experiment, dataset, statistics or a claim that evidence proves something',
  product_or_service_proposal: 'a concrete product, service, feature, launch, brand or value-proposition proposal',
  market_or_competitor_claim: 'a market, customer-demand, competitor, uniqueness, positioning or go-to-market claim',
  pricing_revenue_forecast_or_funding: 'pricing, revenue, margin, forecast, ROI, budget, runway or funding assertion',
  visible_interface_or_user_workflow: 'a user interface, form, onboarding, workflow, warning, recovery or accessibility concern',
  technical_components_or_integration: 'architecture components, database, queue, model, integration, deployment or technical contract',
  scale_reliability_or_migration: 'scale, latency, availability, resilience, capacity, migration or recovery requirement',
  identity_credentials_or_permissions: 'login, identity, credentials, roles, permissions, access control or privileged boundary',
  personal_or_sensitive_data_processing: 'concrete collection, storage, sharing, monitoring or decision use of personal or sensitive data',
  api_upload_webhook_or_agent_tool: 'internet-facing API, file upload, webhook, agent tool or similarly concrete attack surface',
  security_incident_vulnerability_or_secret: 'security incident, vulnerability, exposed secret, threat or explicit security-control concern',
  payment_processing_or_financial_data: 'payment execution, card or bank data, wallet, lending, insurance or investment flow',
  consumer_terms_marketing_or_auto_renewal: 'consumer terms, advertised price, subscription renewal, cancellation or marketing qualification',
  contract_ip_licence_or_liability: 'contract, intellectual property, licence, liability, indemnity or confidentiality issue',
  regulated_activity: 'a specifically regulated activity, profession, product or cross-border obligation',
  government_public_funds_or_public_service: 'government, regulator, public funds, public procurement or delivery of a public service',
  policy_legislation_or_procurement: 'policy, legislation, consultation, regulatory change or public procurement decision',
  high_stakes_automated_decision: 'automated or AI-supported decision affecting rights, eligibility, employment, health or essential services',
  surveillance_biometrics_or_persuasion: 'surveillance, biometrics, profiling, manipulation, political influence or targeted persuasion',
  children_or_vulnerable_people: 'children or people whose vulnerability or dependency materially changes potential harm',
  worker_monitoring_or_automated_management: 'worker monitoring, scoring, scheduling or automated management',
  sleep_caffeine_or_fatigue: 'sleep timing or quality, insomnia, fatigue, or caffeine and another named stimulant where timing or intake has a plausible sleep consequence',
  personal_health_symptom_or_medication: 'a named symptom, health condition, medicine, supplement, pregnancy, or request for personalised health guidance',
  urgent_health_red_flag: 'a credible acute, severe or rapidly worsening health danger requiring urgent clinical triage',
  delivery_roadmap_or_ownership: 'roadmap, implementation plan, milestones, owners, dependencies or acceptance criteria',
  operational_change_or_rollout: 'rollout, migration, support, training, adoption, operating model, handover or rollback',
  physical_or_operational_safety: 'credible physical, clinical or operational safety consequence'
}

interface RoutingRule {
  strong: RoutingSignalId[]
  supporting: RoutingSignalId[]
  mandatory: RoutingSignalId[]
  lensAffinity: AnalysisMode[]
}

const RULES: Record<ExpertId, RoutingRule> = {
  cyber_security_privacy: {
    strong: ['identity_credentials_or_permissions', 'personal_or_sensitive_data_processing', 'api_upload_webhook_or_agent_tool', 'security_incident_vulnerability_or_secret', 'payment_processing_or_financial_data'],
    supporting: ['technical_components_or_integration', 'scale_reliability_or_migration'],
    mandatory: ['security_incident_vulnerability_or_secret'],
    lensAffinity: ['security']
  },
  ux_accessibility: {
    strong: ['visible_interface_or_user_workflow'],
    supporting: ['audience_facing_prose', 'concrete_editorial_risk', 'children_or_vulnerable_people'],
    mandatory: [], lensAffinity: ['general']
  },
  finance_commercial: {
    strong: ['pricing_revenue_forecast_or_funding', 'payment_processing_or_financial_data'],
    supporting: ['market_or_competitor_claim', 'product_or_service_proposal', 'regulated_activity'],
    mandatory: ['payment_processing_or_financial_data'], lensAffinity: ['strategy']
  },
  legal_regulatory: {
    strong: ['personal_or_sensitive_data_processing', 'consumer_terms_marketing_or_auto_renewal', 'contract_ip_licence_or_liability', 'regulated_activity'],
    supporting: ['government_public_funds_or_public_service', 'high_stakes_automated_decision', 'surveillance_biometrics_or_persuasion', 'children_or_vulnerable_people', 'worker_monitoring_or_automated_management'],
    mandatory: ['personal_or_sensitive_data_processing', 'regulated_activity', 'high_stakes_automated_decision', 'surveillance_biometrics_or_persuasion', 'children_or_vulnerable_people', 'worker_monitoring_or_automated_management'],
    lensAffinity: ['general']
  },
  public_policy: {
    strong: ['government_public_funds_or_public_service', 'policy_legislation_or_procurement'],
    supporting: ['high_stakes_automated_decision', 'regulated_activity'],
    mandatory: ['government_public_funds_or_public_service'], lensAffinity: ['strategy']
  },
  ethics_societal: {
    strong: ['high_stakes_automated_decision', 'surveillance_biometrics_or_persuasion', 'children_or_vulnerable_people', 'worker_monitoring_or_automated_management', 'physical_or_operational_safety'],
    supporting: ['personal_or_sensitive_data_processing', 'government_public_funds_or_public_service'],
    mandatory: ['high_stakes_automated_decision', 'surveillance_biometrics_or_persuasion', 'children_or_vulnerable_people', 'worker_monitoring_or_automated_management', 'physical_or_operational_safety'],
    lensAffinity: ['strategy']
  },
  technical_architecture: {
    strong: ['technical_components_or_integration', 'scale_reliability_or_migration', 'api_upload_webhook_or_agent_tool'],
    supporting: ['identity_credentials_or_permissions', 'delivery_roadmap_or_ownership', 'operational_change_or_rollout'],
    mandatory: [], lensAffinity: ['security', 'delivery']
  },
  product_uniqueness: {
    strong: ['product_or_service_proposal', 'market_or_competitor_claim'],
    supporting: ['claim_or_argument', 'pricing_revenue_forecast_or_funding', 'visible_interface_or_user_workflow'],
    mandatory: [], lensAffinity: ['strategy']
  },
  writing_editorial: {
    strong: ['explicit_language_review', 'concrete_editorial_risk'],
    supporting: ['audience_facing_prose'],
    mandatory: [], lensAffinity: ['writing']
  },
  evidence_research: {
    strong: ['citations_statistics_or_research'],
    supporting: ['claim_or_argument', 'market_or_competitor_claim', 'pricing_revenue_forecast_or_funding'],
    mandatory: [], lensAffinity: ['general', 'strategy']
  },
  health_wellbeing: {
    strong: ['sleep_caffeine_or_fatigue', 'personal_health_symptom_or_medication'],
    supporting: ['children_or_vulnerable_people', 'physical_or_operational_safety'],
    mandatory: ['urgent_health_red_flag'],
    lensAffinity: ['general']
  },
  delivery_operations: {
    strong: ['delivery_roadmap_or_ownership', 'operational_change_or_rollout'],
    supporting: ['technical_components_or_integration', 'scale_reliability_or_migration'],
    mandatory: [], lensAffinity: ['delivery']
  }
}

const FOCUS_PATTERNS: Array<[ExpertId, RegExp]> = [
  ['cyber_security_privacy', /\b(cyber|security|privacy|authentication|authorisation|authorization|credential|vulnerability|threat)\b/i],
  ['ux_accessibility', /\b(user experience|ux|usability|accessibility|wcag|interface|workflow)\b/i],
  ['finance_commercial', /\b(finance|financial|commercial|pricing|revenue|margin|forecast|budget|funding|roi|runway)\b/i],
  ['legal_regulatory', /\b(legal|law|gdpr|regulat|compliance|contract|licen[cs]e|liability|intellectual property|ip rights)\b/i],
  ['public_policy', /\b(public policy|government|public sector|legislation|procurement|regulator)\b/i],
  ['ethics_societal', /\b(ethic|bias|fairness|societal|human rights|surveillance|vulnerable|children)\b/i],
  ['technical_architecture', /\b(architecture|technical design|api|database|integration|scalability|reliability|deployment|rag)\b/i],
  ['product_uniqueness', /\b(product|market|competitor|unique|differentiation|positioning|customer need|value proposition)\b/i],
  ['writing_editorial', /\b(grammar|spelling|punctuation|proofread|edit|rewrite|wording|tone|clarity|plain english|british english|uk english)\b/i],
  ['evidence_research', /\b(evidence|research|citation|source|study|statistics|methodology|fact.?check)\b/i],
  ['health_wellbeing', /\b(health|wellbeing|sleep|insomnia|fatigue|caffeine|coffee|cappuccino|nutrition|diet|symptom|medicine|medication|supplement)\b/i],
  ['delivery_operations', /\b(delivery|implementation|roadmap|milestone|rollout|migration|operating model|operations|ownership|change management)\b/i]
]

interface Candidate extends ExpertSelection {
  score: number
}

function requestedExperts(focusQuestion: string): Set<ExpertId> {
  return new Set(FOCUS_PATTERNS.filter(([, pattern]) => pattern.test(focusQuestion)).map(([id]) => id))
}

function effectiveSignals(observation: Observation): Map<RoutingSignalId, ObservedSignal> {
  const evidenceConfidence = new Map(observation.evidence.map((item) => [item.id, item.confidence]))
  const signals = new Map<RoutingSignalId, ObservedSignal>()
  for (const signal of observation.signals) {
    const confidence = Math.min(
      signal.confidence,
      ...signal.evidenceIds.map((id) => evidenceConfidence.get(id) ?? 0)
    )
    if (confidence < 0.6) continue
    const current = signals.get(signal.signalId)
    if (!current || confidence > current.confidence) {
      signals.set(signal.signalId, { ...signal, confidence })
    }
  }
  return signals
}

function reasonFor(expertId: ExpertId, signalIds: RoutingSignalId[], requested: boolean): string {
  if (requested && signalIds.length === 0) return `The focus question explicitly asks for ${EXPERT_LABELS[expertId]}.`
  const labels = signalIds.slice(0, 2).map((id) => ROUTING_SIGNAL_DESCRIPTIONS[id])
  const prefix = requested ? 'The focus question and supplied evidence indicate' : 'The supplied evidence indicates'
  return `${prefix} ${labels.join(' and ')}.`
}

export function selectExperts(
  observation: Observation,
  source: AnalysisSource,
  depth: ReviewDepth,
  mode: AnalysisMode,
  focusQuestion: string
): ExpertSelection[] {
  const signals = effectiveSignals(observation)
  const requested = requestedExperts(focusQuestion)
  if (mode === 'writing') requested.add('writing_editorial')
  const fallbackEvidence = observation.evidence[0]?.id ? [observation.evidence[0].id] : []

  const candidates = (Object.entries(RULES) as Array<[ExpertId, RoutingRule]>).flatMap(
    ([expertId, rule]): Candidate[] => {
      const strong = rule.strong.flatMap((id) => signals.has(id) ? [signals.get(id)!] : [])
      const supporting = rule.supporting.flatMap((id) => signals.has(id) ? [signals.get(id)!] : [])
      const mandatorySignals = rule.mandatory.flatMap((id) => {
        const signal = signals.get(id)
        return signal && signal.confidence >= 0.82 ? [signal] : []
      })
      const explicitlyRequested = requested.has(expertId)
      const voiceSurfaceSuppressed = source === 'voice_transcript' && expertId === 'writing_editorial' && !explicitlyRequested
      if (voiceSurfaceSuppressed) return []

      let score = 0
      if (strong.some((item) => item.confidence >= 0.72)) {
        score = 0.75 + Math.max(...strong.map((item) => item.confidence)) * 0.15
      } else if (supporting.filter((item) => item.confidence >= 0.68).length >= 2) {
        score = 0.72 + Math.min(0.12, supporting.length * 0.04)
      }
      if (rule.lensAffinity.includes(mode) && score > 0) score = Math.min(0.95, score + 0.04)
      if (explicitlyRequested) score = Math.max(score, 0.88)
      if (mandatorySignals.length > 0) score = 0.99
      if (score < 0.75) return []

      const used = [...mandatorySignals, ...strong, ...supporting]
        .filter((item, index, items) => items.findIndex((other) => other.signalId === item.signalId) === index)
      const signalIds = used.map((item) => item.signalId)
      const evidenceIds = [...new Set(used.flatMap((item) => item.evidenceIds))].slice(0, 6)
      return [{
        expertId,
        score,
        relevance: Number(score.toFixed(2)),
        evidenceIds: evidenceIds.length > 0 ? evidenceIds : fallbackEvidence,
        signalIds,
        explicitlyRequested,
        mandatory: mandatorySignals.length > 0,
        reason: reasonFor(expertId, signalIds, explicitlyRequested)
      }]
    }
  )

  candidates.sort((a, b) =>
    Number(b.mandatory) - Number(a.mandatory) ||
    Number(b.explicitlyRequested) - Number(a.explicitlyRequested) ||
    b.score - a.score ||
    a.expertId.localeCompare(b.expertId)
  )

  if (candidates.length === 0) {
    return [{
      expertId: 'evidence_research',
      relevance: 0.75,
      evidenceIds: fallbackEvidence,
      signalIds: signals.has('claim_or_argument') ? ['claim_or_argument'] : [],
      explicitlyRequested: false,
      mandatory: false,
      reason: 'No specialist threshold was met, so Evidence & Research will test the supplied claim without assuming another domain.'
    }]
  }

  const mandatory = candidates.filter((item) => item.mandatory)
  const ordinary = candidates.filter((item) => !item.mandatory)
  const selected = depth === 'focused'
    ? [...mandatory, ...ordinary.slice(0, 1)]
    : [...mandatory, ...ordinary.slice(0, 4)]
  return selected
    .filter((item, index, items) => items.findIndex((other) => other.expertId === item.expertId) === index)
    .slice(0, 6)
    .map(({ score: _score, ...selection }) => selection)
}

export function routingSignalCatalog(): Array<{ id: RoutingSignalId; description: string }> {
  return ROUTING_SIGNAL_IDS.map((id) => ({ id, description: ROUTING_SIGNAL_DESCRIPTIONS[id] }))
}

export function evidenceForSelection(
  observation: Observation,
  selection: ExpertSelection
): Observation['evidence'] {
  const allowed = new Set(selection.evidenceIds)
  return observation.evidence.filter((item) => allowed.has(item.id))
}
