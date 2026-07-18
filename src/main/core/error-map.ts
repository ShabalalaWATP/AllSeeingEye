import type { UserError } from '../../shared/types'

// Maps any thrown value to a fixed, friendly user message. Raw error text is
// never surfaced: it can contain stack traces or fragments of request payloads.

interface ErrorLike {
  name?: unknown
  status?: unknown
  code?: unknown
  message?: unknown
  error?: { code?: unknown }
}

function asErrorLike(err: unknown): ErrorLike {
  return typeof err === 'object' && err !== null ? (err as ErrorLike) : {}
}

function statusOf(e: ErrorLike): number | undefined {
  return typeof e.status === 'number' ? e.status : undefined
}

function codeOf(e: ErrorLike): string {
  const code = e.code ?? e.error?.code
  return typeof code === 'string' ? code : ''
}

function nameOf(e: ErrorLike): string {
  return typeof e.name === 'string' ? e.name : ''
}

function messageOf(e: ErrorLike): string {
  return typeof e.message === 'string' ? e.message : ''
}

const NETWORK_CODES = ['ENOTFOUND', 'ECONNREFUSED', 'ECONNRESET', 'EAI_AGAIN', 'EPIPE']

export function toUserError(err: unknown, model: string): UserError {
  const e = asErrorLike(err)
  const name = nameOf(e)
  const status = statusOf(e)
  const code = codeOf(e)
  const message = messageOf(e)

  if (name === 'MissingKeyError') {
    return {
      code: 'missing_key',
      message: 'No OpenAI API key found. Add OPENAI_API_KEY to your .env file and restart.'
    }
  }
  if (name === 'CaptureError') {
    return {
      code: 'capture_failed',
      message: 'Could not capture the screen. Try again, or use the text tab.'
    }
  }
  if (name === 'ZodError' || name === 'BadResponseError') {
    return { code: 'bad_response', message: 'The model returned an unexpected format. Try again.' }
  }
  if (status === 401 || status === 403) {
    return {
      code: 'invalid_key',
      message: 'The OpenAI API key was rejected. Check OPENAI_API_KEY in your .env file.'
    }
  }
  if (status === 404 || code === 'model_not_found') {
    return {
      code: 'model_unavailable',
      message: `The model '${model}' is not available on this account. Set OPENAI_MODEL to a model you can use.`
    }
  }
  if (status === 429 && code === 'insufficient_quota') {
    return { code: 'quota', message: 'The OpenAI account is out of quota. Check billing.' }
  }
  if (status === 429) {
    return {
      code: 'rate_limited',
      message: 'OpenAI is rate limiting requests. Wait a moment and try again.'
    }
  }
  if (name.includes('Timeout') || code === 'ETIMEDOUT' || /timed?[ _]?out/i.test(message)) {
    return { code: 'timeout', message: 'The analysis took too long and was stopped. Try again.' }
  }
  if (
    name === 'APIConnectionError' ||
    NETWORK_CODES.includes(code) ||
    message.includes('fetch failed')
  ) {
    return { code: 'network', message: 'Could not reach OpenAI. Check your internet connection.' }
  }
  return { code: 'unknown', message: 'Something went wrong. Try again.' }
}
