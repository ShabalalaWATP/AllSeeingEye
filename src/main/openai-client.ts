import OpenAI from 'openai'
import { zodTextFormat } from 'openai/helpers/zod'
import { RedTeamFindingSchema, sanitiseFinding } from './core/finding-schema'
import { buildInstruction, USER_PROMPT_SCREEN, USER_PROMPT_TEXT } from './core/prompts'
import { BadResponseError, MissingKeyError } from './core/errors'
import type { AnalysisMode, RedTeamFinding } from '../shared/types'

const TIMEOUT_MS = 45_000
const DEFAULT_MODEL = 'gpt-5.6'

let client: OpenAI | null = null

export function hasApiKey(): boolean {
  return Boolean(process.env.OPENAI_API_KEY)
}

export function getModel(): string {
  return process.env.OPENAI_MODEL ?? DEFAULT_MODEL
}

function getClient(): OpenAI {
  if (!hasApiKey()) throw new MissingKeyError()
  client ??= new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
    timeout: TIMEOUT_MS,
    maxRetries: 1
  })
  return client
}

async function run(instruction: string, userContent: unknown[]): Promise<RedTeamFinding> {
  const openai = getClient()
  const request: Record<string, unknown> = {
    model: getModel(),
    input: [
      { role: 'system', content: instruction },
      { role: 'user', content: userContent }
    ],
    text: { format: zodTextFormat(RedTeamFindingSchema, 'red_team_finding') }
  }
  // Only sent when explicitly configured: non-reasoning models reject it.
  const effort = process.env.OPENAI_REASONING_EFFORT
  if (effort) request.reasoning = { effort }

  // The request shape follows the documented Responses API; the loose cast
  // keeps us compatible across SDK minor versions. The output is fully
  // re-validated locally, so nothing downstream trusts the cast.
  const response = await openai.responses.parse(request as never)
  const parsed = (response as { output_parsed?: unknown }).output_parsed
  if (!parsed) throw new BadResponseError('empty structured output')
  return sanitiseFinding(RedTeamFindingSchema.parse(parsed))
}

export async function analyseImage(dataUrl: string, mode: AnalysisMode): Promise<RedTeamFinding> {
  return run(buildInstruction(mode, 'screen'), [
    { type: 'input_text', text: USER_PROMPT_SCREEN },
    { type: 'input_image', image_url: dataUrl, detail: 'high' }
  ])
}

export async function analyseText(text: string, mode: AnalysisMode): Promise<RedTeamFinding> {
  return run(buildInstruction(mode, 'text'), [
    { type: 'input_text', text: `${USER_PROMPT_TEXT}\n\n---\n${text}` }
  ])
}
