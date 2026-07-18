import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { CompanionState, Severity, StatePayload } from '../../shared/types'

const INITIAL_SNAPSHOT: StatePayload = {
  state: 'idle',
  windowMode: 'eye',
  analysisMode: 'general',
  reviewDepth: 'focused',
  paused: false,
  privacyNoticeDismissed: true,
  finding: null,
  quickResult: null,
  report: null,
  error: null,
  reviewPhase: null,
  canRunFullReview: false
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

// Small allowance for panel margins outside the measured element.
const FIT_HEIGHT_PAD_PX = 8

/**
 * Auto-size the window to its content: measures the referenced element and
 * asks main to fit the window height (clamped there) whenever it changes.
 */
export function useFitHeight<T extends HTMLElement>(): React.RefObject<T | null> {
  const ref = useRef<T>(null)
  useLayoutEffect(() => {
    const element = ref.current
    if (!element) return
    let last = 0
    const send = (): void => {
      const height = Math.ceil(element.getBoundingClientRect().height) + FIT_HEIGHT_PAD_PX
      if (Math.abs(height - last) < 2) return
      last = height
      void window.criticalEye.fitHeight(height)
    }
    const observer = new ResizeObserver(send)
    observer.observe(element)
    send()
    return () => observer.disconnect()
  }, [])
  return ref
}

export function statusText(
  state: CompanionState,
  elapsed: number,
  reviewPhase: StatePayload['reviewPhase'] = null
): string {
  switch (state) {
    case 'capturing':
      return 'Capturing'
    case 'recording':
      return 'Listening…'
    case 'transcribing':
      return 'Transcribing'
    case 'analysing':
      if (reviewPhase === 'full') {
        return elapsed > 0
          ? `Running the relevant expert review… ${elapsed}s`
          : 'Running the relevant expert review…'
      }
      return elapsed > 0 ? `Getting a quick take… ${elapsed}s` : 'Getting a quick take…'
    case 'paused':
      return 'Paused'
    case 'error':
      return 'Unable to analyse'
    case 'quick_result':
      return 'Quick take ready'
    default:
      return 'Ready'
  }
}

export function isBusy(state: CompanionState): boolean {
  return state === 'capturing' ||
    state === 'recording' ||
    state === 'transcribing' ||
    state === 'analysing'
}

export function prettifyCategory(category: string): string {
  return category.replace(/_/g, ' ')
}

export function severityClass(severity: Severity): string {
  return `sev-${severity}`
}
