import { describe, expect, it, vi } from 'vitest'
import { AnalysisSession } from '../src/main/core/analysis-session'

const pendingInput = {
  runId: '11111111-1111-4111-8111-111111111111',
  source: 'text' as const,
  artefact: 'private input',
  focusQuestion: ''
}

describe('AnalysisSession', () => {
  it('aborts the active provider request and invalidates stale completions', () => {
    const session = new AnalysisSession(() => undefined)
    const generation = session.nextGeneration()
    const operation = session.startAbortableOperation()
    session.invalidate()
    expect(operation.signal.aborted).toBe(true)
    expect(session.isCurrent(generation)).toBe(false)
  })

  it('actively expires a pending full-review hand-off', () => {
    vi.useFakeTimers()
    try {
      const expired = vi.fn()
      const session = new AnalysisSession(expired)
      session.retainPending(pendingInput)
      vi.advanceTimersByTime(5 * 60 * 1_000)
      expect(expired).toHaveBeenCalledOnce()
      expect(session.hasPending(pendingInput.runId)).toBe(false)
    } finally {
      vi.useRealTimers()
    }
  })
})
