import { toFile } from 'openai'
import {
  CombinedSynthesisSchema,
  ExpertAnalysisSchema,
  ObservationSchema,
  sanitiseExpertAnalysis,
  sanitiseSynthesis,
  type EvidenceItem,
  type ObservationRoute
} from './agents/schemas'
import {
  buildExpertInstruction,
  buildExpertUserContent,
  buildRouterInstruction,
  buildSynthesisInstruction,
  buildSynthesisUserContent
} from './agents/prompts'
import { selectExperts } from './agents/routing'
import { BadResponseError } from './core/errors'
import {
  getOpenAIClient,
  runStructured
} from './openai-service'
import type {
  AnalysisMode,
  AnalysisSource,
  CombinedSynthesis,
  ExpertAnalysis,
  ExpertId,
  ReviewDepth,
  VoiceMimeType
} from '../shared/types'
import { MAX_TEXT_LENGTH } from '../shared/types'

export { getModel, hasApiKey } from './openai-service'

export async function observeAndRoute(
  source: AnalysisSource,
  artefact: string,
  mode: AnalysisMode,
  depth: ReviewDepth,
  focusQuestion: string,
  signal?: AbortSignal
): Promise<ObservationRoute> {
  const prompt = `Review focus: ${focusQuestion || 'No specific question; assess the overall work.'}`
  const content: unknown[] = source === 'screen'
    ? [
        { type: 'input_text', text: prompt },
        { type: 'input_image', image_url: artefact, detail: 'high' }
      ]
    : [{ type: 'input_text', text: `${prompt}\n\nSupplied work:\n---\n${artefact}` }]
  const observation = await runStructured(
    buildRouterInstruction(source, depth, mode),
    content,
    ObservationSchema,
    'critical_eye_observation_route',
    { signal }
  )
  return {
    ...observation,
    selectedExperts: selectExperts(observation, source, depth, mode, focusQuestion)
  }
}

export async function runExpert(
  expertId: ExpertId,
  evidence: EvidenceItem[],
  subjectSummary: string,
  limitations: string[],
  focusQuestion: string,
  mode: AnalysisMode,
  source: AnalysisSource,
  signal?: AbortSignal
): Promise<ExpertAnalysis> {
  const result = await runStructured(
    buildExpertInstruction(expertId),
    [{
      type: 'input_text',
      text: buildExpertUserContent(evidence, subjectSummary, limitations, focusQuestion, mode, source)
    }],
    ExpertAnalysisSchema,
    `critical_eye_${expertId}`,
    { signal }
  )
  return sanitiseExpertAnalysis(result, expertId, evidence)
}

export async function synthesiseExperts(
  analyses: ExpertAnalysis[],
  focusQuestion: string,
  signal?: AbortSignal
): Promise<CombinedSynthesis> {
  const result = await runStructured(
    buildSynthesisInstruction(),
    [{ type: 'input_text', text: buildSynthesisUserContent(analyses, focusQuestion) }],
    CombinedSynthesisSchema,
    'critical_eye_combined_analysis',
    { signal }
  )
  return sanitiseSynthesis(result)
}

export async function transcribeVoice(
  bytes: Uint8Array,
  mimeType: VoiceMimeType,
  signal?: AbortSignal
): Promise<string> {
  const baseMime = mimeType.split(';')[0]
  const extension = baseMime === 'audio/mp4'
    ? 'm4a'
    : baseMime === 'audio/mpeg'
      ? 'mp3'
      : baseMime === 'audio/wav'
        ? 'wav'
        : baseMime === 'audio/ogg'
          ? 'ogg'
          : 'webm'
  const audioCopy = Buffer.from(bytes)
  try {
    const file = await toFile(audioCopy, `voice-note.${extension}`, { type: baseMime })
    const result = await getOpenAIClient().audio.transcriptions.create(
      {
        file,
        model: process.env.OPENAI_TRANSCRIPTION_MODEL ?? 'gpt-4o-transcribe',
        response_format: 'json'
      },
      signal ? { signal } : undefined
    )
    const transcript = result.text.trim()
    if (!transcript) throw new BadResponseError('empty voice transcription')
    if (transcript.length > MAX_TEXT_LENGTH) {
      throw new BadResponseError('voice transcription is too long to analyse')
    }
    return transcript
  } finally {
    audioCopy.fill(0)
  }
}
