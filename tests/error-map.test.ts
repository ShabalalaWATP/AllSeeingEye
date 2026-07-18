import { describe, expect, it } from 'vitest'
import { toUserError } from '../src/main/core/error-map'
import { BadResponseError, CaptureError, MissingKeyError } from '../src/main/core/errors'

const MODEL = 'gpt-5.6'

describe('toUserError', () => {
  it('maps a missing key', () => {
    expect(toUserError(new MissingKeyError(), MODEL).code).toBe('missing_key')
  })

  it('maps capture failures', () => {
    expect(toUserError(new CaptureError('boom'), MODEL).code).toBe('capture_failed')
  })

  it('maps schema and parse failures', () => {
    expect(toUserError(new BadResponseError(), MODEL).code).toBe('bad_response')
    expect(toUserError({ name: 'ZodError' }, MODEL).code).toBe('bad_response')
  })

  it('maps rejected keys', () => {
    expect(toUserError({ status: 401 }, MODEL).code).toBe('invalid_key')
    expect(toUserError({ status: 403 }, MODEL).code).toBe('invalid_key')
  })

  it('maps an unavailable model and names it', () => {
    const byStatus = toUserError({ status: 404 }, MODEL)
    expect(byStatus.code).toBe('model_unavailable')
    expect(byStatus.message).toContain(MODEL)
    expect(toUserError({ code: 'model_not_found' }, MODEL).code).toBe('model_unavailable')
  })

  it('distinguishes quota exhaustion from rate limiting', () => {
    expect(toUserError({ status: 429, code: 'insufficient_quota' }, MODEL).code).toBe('quota')
    expect(toUserError({ status: 429, error: { code: 'insufficient_quota' } }, MODEL).code).toBe(
      'quota'
    )
    expect(toUserError({ status: 429 }, MODEL).code).toBe('rate_limited')
  })

  it('maps timeouts', () => {
    expect(toUserError({ name: 'APIConnectionTimeoutError' }, MODEL).code).toBe('timeout')
    expect(toUserError({ code: 'ETIMEDOUT' }, MODEL).code).toBe('timeout')
    expect(toUserError({ message: 'Request timed out' }, MODEL).code).toBe('timeout')
  })

  it('maps connectivity failures', () => {
    expect(toUserError({ name: 'APIConnectionError' }, MODEL).code).toBe('network')
    expect(toUserError({ code: 'ENOTFOUND' }, MODEL).code).toBe('network')
    expect(toUserError({ message: 'TypeError: fetch failed' }, MODEL).code).toBe('network')
  })

  it('maps anything else to unknown without leaking detail', () => {
    expect(toUserError('boom', MODEL).code).toBe('unknown')
    expect(toUserError(null, MODEL).code).toBe('unknown')
    expect(toUserError(undefined, MODEL).code).toBe('unknown')
    expect(toUserError(new Error('secret internal detail'), MODEL).message).not.toContain(
      'secret internal detail'
    )
  })

  it('never leaks anything key-shaped or a stack trace', () => {
    const samples = [
      new MissingKeyError(),
      new CaptureError(),
      new BadResponseError(),
      { status: 401 },
      { status: 404 },
      { status: 429 },
      { status: 429, code: 'insufficient_quota' },
      { name: 'APIConnectionTimeoutError' },
      { name: 'APIConnectionError' },
      new Error('Bearer sk-proj-abc123 at Object.<anonymous>')
    ]
    for (const sample of samples) {
      const { message } = toUserError(sample, MODEL)
      expect(message).not.toMatch(/sk-/)
      expect(message).not.toMatch(/at Object/)
    }
  })
})
