import type { AnalysisSource } from '../../shared/types'

export const PENDING_REVIEW_TTL_MS = 5 * 60 * 1_000

export interface PendingReviewInput {
  runId: string
  source: AnalysisSource
  artefact: string
  focusQuestion: string
}

export interface PendingReview extends PendingReviewInput {
  expiresAt: number
}

/** One exact, short-lived hand-off from a quick take to the expert board. */
export class PendingReviewStore {
  private current: PendingReview | null = null

  retain(input: PendingReviewInput, now = Date.now()): PendingReview {
    this.clear()
    this.current = { ...input, expiresAt: now + PENDING_REVIEW_TTL_MS }
    return this.current
  }

  has(runId: string, now = Date.now()): boolean {
    return this.peek(now)?.runId === runId
  }

  peek(now = Date.now()): PendingReview | null {
    if (this.current && this.current.expiresAt <= now) this.clear()
    return this.current
  }

  /** Atomically consumes the matching run. Stale or replayed IDs are rejected. */
  take(runId: string, now = Date.now()): PendingReview | null {
    const value = this.peek(now)
    if (!value || value.runId !== runId) return null
    this.current = null
    return value
  }

  clear(): void {
    if (this.current) this.current.artefact = ''
    this.current = null
  }
}
