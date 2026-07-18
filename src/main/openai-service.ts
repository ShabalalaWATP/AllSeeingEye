import OpenAI from 'openai'
import { zodTextFormat } from 'openai/helpers/zod'
import type { z } from 'zod'
import { BadResponseError, MissingKeyError } from './core/errors'

const TIMEOUT_MS = 45_000
const DEFAULT_MODEL = 'gpt-5.6-luna'

let client: OpenAI | null = null

export function hasApiKey(): boolean {
  return Boolean(process.env.OPENAI_API_KEY)
}

export function getModel(): string {
  return process.env.OPENAI_MODEL ?? DEFAULT_MODEL
}

export function getOpenAIClient(): OpenAI {
  if (!hasApiKey()) throw new MissingKeyError()
  client ??= new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
    timeout: TIMEOUT_MS,
    maxRetries: 1
  })
  return client
}

export async function runStructured<T>(
  instruction: string,
  userContent: unknown[],
  schema: z.ZodType<T>,
  schemaName: string,
  options: { reasoningEffort?: string | null; signal?: AbortSignal } = {}
): Promise<T> {
  const request: Record<string, unknown> = {
    model: getModel(),
    input: [
      { role: 'system', content: instruction },
      { role: 'user', content: userContent }
    ],
    text: { format: zodTextFormat(schema, schemaName) },
    store: false
  }
  const effort = options.reasoningEffort === undefined
    ? process.env.OPENAI_REASONING_EFFORT
    : options.reasoningEffort
  if (effort) request.reasoning = { effort }

  const response = await getOpenAIClient().responses.parse(
    request as never,
    options.signal ? { signal: options.signal } : undefined
  )
  const parsed = (response as { output_parsed?: unknown }).output_parsed
  if (!parsed) throw new BadResponseError('empty or refused structured output')
  return schema.parse(parsed)
}
