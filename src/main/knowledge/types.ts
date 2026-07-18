import type { ExpertId } from '../../shared/types'

export type SourceStatus =
  | 'binding'
  | 'mandatory_in_scope'
  | 'official_guidance'
  | 'voluntary_framework'
  | 'informative'
  | 'future_or_volatile'

export interface KnowledgeSource {
  id: string
  title: string
  authority: string
  url: string
  jurisdiction: string
  status: SourceStatus
  lastVerified: string
}

export interface KnowledgeNote {
  id: string
  statement: string
  sourceRefs: string[]
}

/** Curated prompt-time knowledge. User artefacts are never written into these packs. */
export interface KnowledgePack {
  expertId: ExpertId
  label: string
  version: string
  lastVerified: string
  reviewDue: string
  jurisdictions: string[]
  remit: string
  exclusions: string[]
  hardTriggers: string[]
  softTriggers: string[]
  coRoute: ExpertId[]
  rubric: string[]
  sources: KnowledgeSource[]
  knowledge?: KnowledgeNote[]
  disclaimer: string
}
