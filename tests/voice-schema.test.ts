import { describe, expect, it } from 'vitest'
import { VoiceAnalysisRequestSchema } from '../src/main/core/voice-schema'
import { MAX_VOICE_BYTES, MAX_VOICE_SECONDS } from '../src/shared/types'

function validRequest(): Record<string, unknown> {
  return {
    sessionId: '11111111-1111-4111-8111-111111111111',
    bytes: new ArrayBuffer(32),
    mimeType: 'audio/webm',
    durationMs: 1_000,
    mode: 'general',
    focusQuestion: 'Will this affect my sleep?',
    depth: 'focused'
  }
}

describe('VoiceAnalysisRequestSchema', () => {
  it('accepts the complete automatic voice-analysis request', () => {
    expect(VoiceAnalysisRequestSchema.parse(validRequest())).toEqual(validRequest())
  })

  it('rejects short, empty, oversized and overlong recordings', () => {
    expect(VoiceAnalysisRequestSchema.safeParse({ ...validRequest(), durationMs: 499 }).success).toBe(false)
    expect(VoiceAnalysisRequestSchema.safeParse({ ...validRequest(), bytes: new ArrayBuffer(0) }).success).toBe(false)
    expect(VoiceAnalysisRequestSchema.safeParse({
      ...validRequest(), bytes: new ArrayBuffer(MAX_VOICE_BYTES + 1)
    }).success).toBe(false)
    expect(VoiceAnalysisRequestSchema.safeParse({
      ...validRequest(), durationMs: MAX_VOICE_SECONDS * 1_000 + 1
    }).success).toBe(false)
  })

  it('rejects unsupported formats, invalid settings and extra fields', () => {
    expect(VoiceAnalysisRequestSchema.safeParse({ ...validRequest(), sessionId: 'stale' }).success).toBe(false)
    expect(VoiceAnalysisRequestSchema.safeParse({ ...validRequest(), mimeType: 'audio/aac' }).success).toBe(false)
    expect(VoiceAnalysisRequestSchema.safeParse({ ...validRequest(), mode: 'medical' }).success).toBe(false)
    expect(VoiceAnalysisRequestSchema.safeParse({ ...validRequest(), depth: 'exhaustive' }).success).toBe(false)
    expect(VoiceAnalysisRequestSchema.safeParse({ ...validRequest(), unexpected: true }).success).toBe(false)
  })
})
