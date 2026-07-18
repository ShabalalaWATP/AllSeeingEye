import { describe, expect, it } from 'vitest'
import {
  PENDING_REVIEW_TTL_MS,
  PendingReviewStore,
  type PendingReviewInput
} from '../src/main/core/pending-review'

const first: PendingReviewInput = {
  runId: '11111111-1111-4111-8111-111111111111',
  source: 'text',
  artefact: 'first input',
  focusQuestion: 'What is weakest?'
}

describe('PendingReviewStore', () => {
  it('consumes a matching run exactly once', () => {
    const store = new PendingReviewStore()
    store.retain(first, 1_000)
    expect(store.take(first.runId, 1_001)?.artefact).toBe('first input')
    expect(store.take(first.runId, 1_002)).toBeNull()
  })

  it('rejects a mismatched run without consuming the current input', () => {
    const store = new PendingReviewStore()
    store.retain(first, 1_000)
    expect(store.take('22222222-2222-4222-8222-222222222222', 1_001)).toBeNull()
    expect(store.take(first.runId, 1_002)?.artefact).toBe('first input')
  })

  it('expires at the active retention boundary', () => {
    const store = new PendingReviewStore()
    store.retain(first, 1_000)
    expect(store.has(first.runId, 1_000 + PENDING_REVIEW_TTL_MS - 1)).toBe(true)
    expect(store.has(first.runId, 1_000 + PENDING_REVIEW_TTL_MS)).toBe(false)
    expect(store.take(first.runId, 1_000 + PENDING_REVIEW_TTL_MS)).toBeNull()
  })

  it('replaces an older input', () => {
    const store = new PendingReviewStore()
    store.retain(first, 1_000)
    store.retain({
      ...first,
      runId: '33333333-3333-4333-8333-333333333333',
      source: 'voice_transcript',
      artefact: 'replacement transcript'
    }, 1_100)
    expect(store.take(first.runId, 1_101)).toBeNull()
    expect(store.take('33333333-3333-4333-8333-333333333333', 1_101)?.artefact)
      .toBe('replacement transcript')
  })
})
