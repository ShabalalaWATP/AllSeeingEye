import type { CompanionState } from '../../shared/types'

export const TRANSITIONS: Record<CompanionState, readonly CompanionState[]> = {
  idle: ['capturing', 'analysing', 'paused'],
  capturing: ['analysing', 'error', 'idle'],
  analysing: ['result', 'no_issue', 'error'],
  result: ['idle', 'capturing', 'analysing'],
  no_issue: ['idle', 'capturing', 'analysing'],
  error: ['idle', 'capturing', 'analysing'],
  paused: ['idle']
}

export function canTransition(from: CompanionState, to: CompanionState): boolean {
  return TRANSITIONS[from].includes(to)
}

/** A new analysis may start only when unpaused and nothing is in flight. */
export function canTrigger(paused: boolean, busy: boolean): boolean {
  return !paused && !busy
}

/** The state shown to the user: the paused flag masks a quiet idle state. */
export function displayState(state: CompanionState, paused: boolean): CompanionState {
  if (paused && (state === 'idle' || state === 'paused')) return 'paused'
  return state
}
