import { buildQuickInstruction } from './core/quick-prompt'
import { QuickTakeSchema, sanitiseQuickTake } from './core/quick-take'
import { runStructured } from './openai-service'
import type { AnalysisSource } from '../shared/types'

export async function runQuickAnalysis(
  source: AnalysisSource,
  artefact: string,
  focusQuestion: string,
  signal?: AbortSignal
): Promise<string> {
  const task = focusQuestion
    ? `User's specific question: ${focusQuestion}`
    : 'Give the most useful immediate answer or quick take.'
  const content: unknown[] = source === 'screen'
    ? [
        { type: 'input_text', text: task },
        { type: 'input_image', image_url: artefact, detail: 'high' }
      ]
    : [{ type: 'input_text', text: `${task}\n\nSupplied material:\n---\n${artefact}` }]

  const result = await runStructured(
    buildQuickInstruction(source),
    content,
    QuickTakeSchema,
    'critical_eye_quick_take',
    {
      reasoningEffort: process.env.OPENAI_QUICK_REASONING_EFFORT ?? 'low',
      signal
    }
  )
  return sanitiseQuickTake(result)
}
