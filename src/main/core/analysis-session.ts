import {
  PendingReviewStore,
  type PendingReview,
  type PendingReviewInput
} from './pending-review'

/** Tracks one cancellable analysis operation and one short-lived expansion input. */
export class AnalysisSession {
  private readonly pending = new PendingReviewStore()
  private pendingTimer: ReturnType<typeof setTimeout> | null = null
  private abortController: AbortController | null = null
  private generation = 0

  constructor(private readonly onPendingExpired: () => void) {}

  nextGeneration(): number {
    this.generation += 1
    return this.generation
  }

  isCurrent(generation: number): boolean {
    return generation === this.generation
  }

  startAbortableOperation(): AbortController {
    this.abortController?.abort()
    const controller = new AbortController()
    this.abortController = controller
    return controller
  }

  finishAbortableOperation(controller: AbortController): void {
    if (this.abortController === controller) this.abortController = null
  }

  retainPending(input: PendingReviewInput): PendingReview {
    const pending = this.pending.retain(input)
    this.cancelTimer()
    this.pendingTimer = setTimeout(() => {
      this.pendingTimer = null
      this.pending.peek(Date.now())
      this.onPendingExpired()
    }, Math.max(0, pending.expiresAt - Date.now()))
    this.pendingTimer.unref?.()
    return pending
  }

  hasPending(runId: string): boolean {
    return this.pending.has(runId)
  }

  takePending(runId: string): PendingReview | null {
    const pending = this.pending.take(runId)
    if (pending) this.cancelTimer()
    return pending
  }

  clearPending(): void {
    this.cancelTimer()
    this.pending.clear()
  }

  invalidate(): void {
    this.nextGeneration()
    this.abortController?.abort()
    this.abortController = null
    this.clearPending()
  }

  private cancelTimer(): void {
    if (this.pendingTimer) clearTimeout(this.pendingTimer)
    this.pendingTimer = null
  }
}
