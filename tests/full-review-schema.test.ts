import { describe, expect, it } from 'vitest'
import { FullReviewRequestSchema } from '../src/main/core/full-review-schema'

describe('FullReviewRequestSchema', () => {
  it('accepts an opaque UUID run ID', () => {
    expect(FullReviewRequestSchema.parse({
      runId: '11111111-1111-4111-8111-111111111111'
    })).toEqual({ runId: '11111111-1111-4111-8111-111111111111' })
  })

  it('rejects malformed run IDs', () => {
    expect(() => FullReviewRequestSchema.parse({ runId: 'latest' })).toThrow()
  })

  it('rejects extra fields that could smuggle a replacement source', () => {
    expect(() => FullReviewRequestSchema.parse({
      runId: '11111111-1111-4111-8111-111111111111',
      artefact: 'replacement'
    })).toThrow()
  })
})
