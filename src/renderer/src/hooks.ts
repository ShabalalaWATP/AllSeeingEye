import { useEffect, useState } from 'react'
import type { CompanionState, Severity, StatePayload } from '../../shared/types'

const INITIAL_SNAPSHOT: StatePayload = {
  state: 'idle',
  windowMode: 'eye',
  analysisMode: 'general',
  paused: false,
  privacyNoticeDismissed: true,
  finding: null,
  error: null
}

/** Mirrors the main-process state machine. The renderer never owns state. */
export function useCompanion(): StatePayload {
  const [snapshot, setSnapshot] = useState<StatePayload>(INITIAL_SNAPSHOT)
  useEffect(() => {
    const unsubscribe = window.criticalEye.onState(setSnapshot)
    void window.criticalEye.requestState()
    return unsubscribe
  }, [])
  return snapshot
}

export interface GazeTarget {
  tx: number
  ty: number
}

// Distance at which the pupil reaches maximum deflection.
const SATURATION_PX = 500

/** Normalised gaze target from the main-process global cursor feed. */
export function useCursorTarget(): GazeTarget {
  const [target, setTarget] = useState<GazeTarget>({ tx: 0, ty: 0 })
  useEffect(
    () =>
      window.criticalEye.onCursor(({ dx, dy }) => {
        setTarget({
          tx: Math.max(-1, Math.min(1, dx / SATURATION_PX)),
          // Screen y grows downwards; the shader's y grows upwards.
          ty: Math.max(-1, Math.min(1, -dy / SATURATION_PX))
        })
      }),
    []
  )
  return target
}

/** Whole seconds since `active` last became true. */
export function useElapsed(active: boolean): number {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    if (!active) {
      setSeconds(0)
      return
    }
    const start = Date.now()
    const id = setInterval(() => setSeconds(Math.floor((Date.now() - start) / 1000)), 500)
    return () => clearInterval(id)
  }, [active])
  return seconds
}

export function statusText(state: CompanionState, elapsed: number): string {
  switch (state) {
    case 'capturing':
      return 'Capturing'
    case 'analysing':
      return elapsed > 0 ? `Thinking… ${elapsed}s` : 'Thinking…'
    case 'paused':
      return 'Paused'
    case 'error':
      return 'Unable to analyse'
    default:
      return 'Ready'
  }
}

export function isBusy(state: CompanionState): boolean {
  return state === 'capturing' || state === 'analysing'
}

export function prettifyCategory(category: string): string {
  return category.replace(/_/g, ' ')
}

export function severityClass(severity: Severity): string {
  return `sev-${severity}`
}
