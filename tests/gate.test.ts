import { describe, expect, it } from 'vitest'
import { AnalysisGate } from '../src/main/core/gate'

describe('AnalysisGate', () => {
  it('grants the first acquisition and refuses the second', () => {
    const gate = new AnalysisGate()
    expect(gate.tryAcquire()).toBe(true)
    expect(gate.tryAcquire()).toBe(false)
    expect(gate.isBusy).toBe(true)
  })

  it('can be reacquired after release', () => {
    const gate = new AnalysisGate()
    gate.tryAcquire()
    gate.release()
    expect(gate.isBusy).toBe(false)
    expect(gate.tryAcquire()).toBe(true)
  })

  it('release after a failure path still frees the gate', () => {
    const gate = new AnalysisGate()
    gate.tryAcquire()
    try {
      throw new Error('analysis failed')
    } catch {
      gate.release()
    }
    expect(gate.tryAcquire()).toBe(true)
  })
})
