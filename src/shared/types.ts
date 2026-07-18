// Types shared between the main process, preload and renderer.
// This module must stay dependency-free and side-effect-free.

export const WINDOW_MODE_NAMES = ['eye', 'compact', 'expanded'] as const
export type WindowMode = (typeof WINDOW_MODE_NAMES)[number]

export const ANALYSIS_MODES = ['general', 'strategy', 'security', 'writing', 'delivery'] as const
export type AnalysisMode = (typeof ANALYSIS_MODES)[number]
export type AnalysisSource = 'screen' | 'text' | 'voice_transcript'

export const REVIEW_PHASES = ['quick', 'full'] as const
export type ReviewPhase = (typeof REVIEW_PHASES)[number]

export const REVIEW_DEPTHS = ['focused', 'combined'] as const
export type ReviewDepth = (typeof REVIEW_DEPTHS)[number]

export const EXPERT_IDS = [
  'cyber_security_privacy',
  'ux_accessibility',
  'finance_commercial',
  'legal_regulatory',
  'public_policy',
  'ethics_societal',
  'technical_architecture',
  'product_uniqueness',
  'writing_editorial',
  'evidence_research',
  'health_wellbeing',
  'delivery_operations'
] as const
export type ExpertId = (typeof EXPERT_IDS)[number]

export const EXPERT_LABELS: Record<ExpertId, string> = {
  cyber_security_privacy: 'Cyber Security & Privacy',
  ux_accessibility: 'UX & Accessibility',
  finance_commercial: 'Finance & Commercial',
  legal_regulatory: 'Legal & Regulatory',
  public_policy: 'Public Policy',
  ethics_societal: 'Ethics & Societal Impact',
  technical_architecture: 'Technical Architecture',
  product_uniqueness: 'Product & Differentiation',
  writing_editorial: 'Writing & Editorial Quality',
  evidence_research: 'Evidence & Research Quality',
  health_wellbeing: 'Health, Sleep & Wellbeing',
  delivery_operations: 'Delivery & Operations'
}

export const EXPERT_SHORT_LABELS: Record<ExpertId, string> = {
  cyber_security_privacy: 'Security',
  ux_accessibility: 'UX',
  finance_commercial: 'Finance',
  legal_regulatory: 'Legal',
  public_policy: 'Policy',
  ethics_societal: 'Ethics',
  technical_architecture: 'Architecture',
  product_uniqueness: 'Product',
  writing_editorial: 'Writing',
  evidence_research: 'Evidence',
  health_wellbeing: 'Health',
  delivery_operations: 'Delivery'
}

export const ROUTING_SIGNAL_IDS = [
  'audience_facing_prose',
  'explicit_language_review',
  'concrete_editorial_risk',
  'claim_or_argument',
  'citations_statistics_or_research',
  'product_or_service_proposal',
  'market_or_competitor_claim',
  'pricing_revenue_forecast_or_funding',
  'visible_interface_or_user_workflow',
  'technical_components_or_integration',
  'scale_reliability_or_migration',
  'identity_credentials_or_permissions',
  'personal_or_sensitive_data_processing',
  'api_upload_webhook_or_agent_tool',
  'security_incident_vulnerability_or_secret',
  'payment_processing_or_financial_data',
  'consumer_terms_marketing_or_auto_renewal',
  'contract_ip_licence_or_liability',
  'regulated_activity',
  'government_public_funds_or_public_service',
  'policy_legislation_or_procurement',
  'high_stakes_automated_decision',
  'surveillance_biometrics_or_persuasion',
  'children_or_vulnerable_people',
  'worker_monitoring_or_automated_management',
  'sleep_caffeine_or_fatigue',
  'personal_health_symptom_or_medication',
  'urgent_health_red_flag',
  'delivery_roadmap_or_ownership',
  'operational_change_or_rollout',
  'physical_or_operational_safety'
] as const
export type RoutingSignalId = (typeof ROUTING_SIGNAL_IDS)[number]

export const SEVERITIES = ['low', 'medium', 'high', 'critical'] as const
export type Severity = (typeof SEVERITIES)[number]

export const CATEGORIES = [
  'assumption',
  'logical_gap',
  'contradiction',
  'missing_evidence',
  'security',
  'privacy',
  'feasibility',
  'stakeholder',
  'clarity',
  'bias',
  'legal',
  'finance',
  'policy',
  'ethics',
  'user_experience',
  'accessibility',
  'architecture',
  'uniqueness',
  'research_quality',
  'health',
  'delivery',
  'other'
] as const
export type FindingCategory = (typeof CATEGORIES)[number]

export interface RedTeamFinding {
  hasMaterialIssue: boolean
  category: FindingCategory
  severity: Severity
  headline: string
  explanation: string
  visibleEvidence: string
  recommendation: string
  confidence: number
}

/** A deliberately unscored, uncited first response from one general LLM call. */
export interface QuickResult {
  runId: string
  answer: string
}

export const EVIDENCE_STRENGTHS = ['weak', 'moderate', 'strong'] as const
export type EvidenceStrength = (typeof EVIDENCE_STRENGTHS)[number]

export interface ExpertFinding extends RedTeamFinding {
  expertId: ExpertId
  evidenceIds: string[]
  evidenceStrength: EvidenceStrength
  validationNeeded: string
  sourceRefs: string[]
}

export interface ExpertSelection {
  expertId: ExpertId
  reason: string
  relevance: number
  evidenceIds: string[]
  signalIds: RoutingSignalId[]
  explicitlyRequested: boolean
  mandatory: boolean
}

export interface ExpertAnalysis {
  expertId: ExpertId
  packVersion: string
  applicability: 'relevant' | 'not_relevant' | 'insufficient_context'
  summary: string
  findings: ExpertFinding[]
  assumptions: string[]
  questions: string[]
  disclaimer: string
}

export interface CombinedSynthesis extends RedTeamFinding {
  agreements: string[]
  disagreements: string[]
  prioritisedActions: string[]
}

export interface AnalysisReport {
  runId: string
  depth: ReviewDepth
  focusQuestion: string
  subjectSummary: string
  selectedExperts: ExpertSelection[]
  expertAnalyses: ExpertAnalysis[]
  synthesis: CombinedSynthesis | null
}

export type ErrorCode =
  | 'missing_key'
  | 'invalid_key'
  | 'model_unavailable'
  | 'quota'
  | 'rate_limited'
  | 'timeout'
  | 'network'
  | 'bad_response'
  | 'capture_failed'
  | 'unknown'

export interface UserError {
  code: ErrorCode
  message: string
}

export type CompanionState =
  | 'idle'
  | 'capturing'
  | 'recording'
  | 'transcribing'
  | 'analysing'
  | 'quick_result'
  | 'result'
  | 'no_issue'
  | 'paused'
  | 'error'

export interface Preferences {
  x: number
  y: number
  mode: AnalysisMode
  reviewDepth: ReviewDepth
  privacyNoticeDismissed: boolean
  startPaused: boolean
}

/** Full snapshot pushed from main to the renderer on every change. */
export interface StatePayload {
  state: CompanionState
  windowMode: WindowMode
  analysisMode: AnalysisMode
  reviewDepth: ReviewDepth
  paused: boolean
  privacyNoticeDismissed: boolean
  finding: RedTeamFinding | null
  quickResult: QuickResult | null
  report: AnalysisReport | null
  error: UserError | null
  /** Quick uses one general LLM call; full uses routed experts and knowledge packs. */
  reviewPhase: ReviewPhase | null
  /** True only while the source for a quick take is still held briefly in memory. */
  canRunFullReview: boolean
}

/** Cursor position relative to the eye centre, in desktop pixels. */
export interface CursorPayload {
  dx: number
  dy: number
}

export type CaptureSourceKind = 'display' | 'window'

export interface CaptureSourceOption {
  token: string
  kind: CaptureSourceKind
  label: string
  previewDataUrl: string | null
}

export interface CaptureSourceBatch {
  batchId: string
  expiresAt: number
  sources: CaptureSourceOption[]
}

export type CaptureTarget =
  | { type: 'display-under-pointer' }
  | { type: 'selected'; batchId: string; token: string }

export const MAX_TEXT_LENGTH = 12_000
export const MAX_FOCUS_QUESTION_LENGTH = 1_000
export const MAX_VOICE_BYTES = 10 * 1024 * 1024
export const MAX_VOICE_SECONDS = 120
export const ALLOWED_VOICE_MIME_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg',
  'audio/mp4;codecs=mp4a.40.2',
  'audio/mp4',
  'audio/mpeg',
  'audio/wav'
] as const
export type VoiceMimeType = (typeof ALLOWED_VOICE_MIME_TYPES)[number]
