import { describe, expect, it } from 'vitest'
import { canTransition, canTrigger, displayState } from '../src/main/core/state'

describe('canTransition', () => {
  it('allows the happy path', () => {
    expect(canTransition('idle', 'capturing')).toBe(true)
    expect(canTransition('capturing', 'analysing')).toBe(true)
    expect(canTransition('analysing', 'result')).toBe(true)
    expect(canTransition('analysing', 'quick_result')).toBe(true)
    expect(canTransition('quick_result', 'analysing')).toBe(true)
    expect(canTransition('analysing', 'no_issue')).toBe(true)
    expect(canTransition('result', 'idle')).toBe(true)
    expect(canTransition('idle', 'transcribing')).toBe(true)
    expect(canTransition('idle', 'recording')).toBe(true)
    expect(canTransition('recording', 'transcribing')).toBe(true)
    expect(canTransition('transcribing', 'analysing')).toBe(true)
  })

  it('allows failure paths', () => {
    expect(canTransition('capturing', 'error')).toBe(true)
    expect(canTransition('analysing', 'error')).toBe(true)
    expect(canTransition('error', 'capturing')).toBe(true)
  })

  it('rejects nonsense transitions', () => {
    expect(canTransition('idle', 'result')).toBe(false)
    expect(canTransition('capturing', 'result')).toBe(false)
    expect(canTransition('paused', 'capturing')).toBe(false)
  })
})

describe('canTrigger', () => {
  it('permits a trigger only when unpaused and idle', () => {
    expect(canTrigger(false, false)).toBe(true)
    expect(canTrigger(true, false)).toBe(false)
    expect(canTrigger(false, true)).toBe(false)
    expect(canTrigger(true, true)).toBe(false)
  })
})

describe('displayState', () => {
  it('masks a quiet idle as paused when the pause flag is on', () => {
    expect(displayState('idle', true)).toBe('paused')
    expect(displayState('paused', true)).toBe('paused')
  })

  it('never masks an active analysis', () => {
    expect(displayState('analysing', true)).toBe('analysing')
    expect(displayState('capturing', true)).toBe('capturing')
    expect(displayState('transcribing', true)).toBe('transcribing')
    expect(displayState('recording', true)).toBe('recording')
  })

  it('passes through when unpaused', () => {
    expect(displayState('idle', false)).toBe('idle')
    expect(displayState('result', false)).toBe('result')
  })
})
