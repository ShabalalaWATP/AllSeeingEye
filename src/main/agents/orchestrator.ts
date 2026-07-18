import { randomUUID } from 'node:crypto'
import { buildReport } from './schemas'
import { evidenceForSelection } from './routing'
import { observeAndRoute, runExpert, synthesiseExperts } from '../openai-client'
import type {
  AnalysisMode,
  AnalysisReport,
  AnalysisSource,
  ExpertAnalysis,
  ReviewDepth
} from '../../shared/types'

export async function runExpertBoard(
  source: AnalysisSource,
  artefact: string,
  mode: AnalysisMode,
  depth: ReviewDepth,
  focusQuestion: string,
  runId: string = randomUUID(),
  onArtefactConsumed?: () => void,
  signal?: AbortSignal
): Promise<AnalysisReport> {
  let route
  try {
    route = await observeAndRoute(source, artefact, mode, depth, focusQuestion, signal)
  } finally {
    // Experts receive only the bounded observation evidence. Drop the raw
    // screen/text/transcript reference before their calls begin.
    artefact = ''
    onArtefactConsumed?.()
  }
  const settled = await Promise.allSettled(
    route.selectedExperts.map((selection) =>
      runExpert(
        selection.expertId,
        evidenceForSelection(route, selection),
        `${route.materialType}. ${selection.reason}`,
        route.limitations,
        focusQuestion,
        mode,
        source,
        signal
      )
    )
  )
  const analyses = settled
    .filter((result): result is PromiseFulfilledResult<ExpertAnalysis> => result.status === 'fulfilled')
    .map((result) => result.value)

  if (analyses.length === 0) {
    const failure = settled.find(
      (result): result is PromiseRejectedResult => result.status === 'rejected'
    )
    throw failure?.reason ?? new Error('All selected experts failed')
  }

  const relevantAnalyses = analyses.filter((analysis) => analysis.applicability === 'relevant')
  let synthesis = null
  if (depth === 'combined' && relevantAnalyses.length > 1) {
    try {
      synthesis = await synthesiseExperts(relevantAnalyses, focusQuestion, signal)
    } catch (error) {
      // Successful expert results remain useful. The report adapter will
      // deterministically choose the highest-severity finding as fallback.
      console.warn('[analysis] combined synthesis failed; returning expert results')
    }
  }
  return buildReport(runId, route, depth, focusQuestion, analyses, synthesis)
}
