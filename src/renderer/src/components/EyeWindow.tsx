import { useEffect, useRef, useState } from 'react'
import EyeShell from './EyeShell'
import { isBusy, statusText, type GazeTarget } from '../hooks'
import type { StatePayload } from '../../../shared/types'

export type LauncherAction = 'screen' | 'window' | 'text' | 'voice'

interface EyeWindowProps {
  snapshot: StatePayload
  cursor: GazeTarget
  launcherRequest: number
  onChoose: (action: LauncherAction) => void
}

const OPEN_DELAY_MS = 160
const CLOSE_DELAY_MS = 220

export default function EyeWindow({
  snapshot,
  cursor,
  launcherRequest,
  onChoose
}: EyeWindowProps): React.JSX.Element {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const firstOptionRef = useRef<HTMLButtonElement>(null)
  const openTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const focusFirstRef = useRef(false)
  const suppressFocusOpenRef = useRef(false)
  const trayAvailable = !snapshot.paused && !isBusy(snapshot.state)

  const clearTimers = (): void => {
    if (openTimerRef.current) clearTimeout(openTimerRef.current)
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current)
    openTimerRef.current = null
    closeTimerRef.current = null
  }

  const requestOpen = (focusFirst = false, delay = 0): void => {
    if (!trayAvailable) return
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current)
    closeTimerRef.current = null
    if (open) {
      if (focusFirst) requestAnimationFrame(() => firstOptionRef.current?.focus())
      return
    }
    focusFirstRef.current ||= focusFirst
    if (openTimerRef.current) clearTimeout(openTimerRef.current)
    openTimerRef.current = setTimeout(() => {
      openTimerRef.current = null
      setOpen(true)
    }, delay)
  }

  const requestClose = (delay = CLOSE_DELAY_MS, respectKeyboardFocus = true): void => {
    if (openTimerRef.current) clearTimeout(openTimerRef.current)
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current)
    openTimerRef.current = null
    closeTimerRef.current = setTimeout(() => {
      closeTimerRef.current = null
      const active = document.activeElement
      if (
        respectKeyboardFocus &&
        active instanceof HTMLElement &&
        active.matches(':focus-visible') &&
        rootRef.current?.contains(active)
      ) return
      focusFirstRef.current = false
      setOpen(false)
    }, delay)
  }

  useEffect(() => {
    if (launcherRequest > 0 && trayAvailable) requestOpen(true)
  }, [launcherRequest])

  useEffect(() => {
    if (!trayAvailable) {
      clearTimers()
      setOpen(false)
    }
  }, [trayAvailable])

  useEffect(() => {
    void window.criticalEye.setEyeTrayOpen(open)
    if (open && focusFirstRef.current) {
      focusFirstRef.current = false
      requestAnimationFrame(() => firstOptionRef.current?.focus())
    }
  }, [open])

  useEffect(() => {
    const close = (): void => {
      clearTimers()
      setOpen(false)
    }
    window.addEventListener('blur', close)
    return () => {
      clearTimers()
      window.removeEventListener('blur', close)
      void window.criticalEye.setEyeTrayOpen(false)
    }
  }, [])

  const choose = (action: LauncherAction): void => {
    clearTimers()
    setOpen(false)
    onChoose(action)
  }

  return (
    <div
      ref={rootRef}
      className="eye-window"
      onPointerEnter={() => requestOpen(false, OPEN_DELAY_MS)}
      onPointerLeave={() => requestClose()}
      onPointerDownCapture={() => {
        if (openTimerRef.current) clearTimeout(openTimerRef.current)
        openTimerRef.current = null
        suppressFocusOpenRef.current = true
        queueMicrotask(() => { suppressFocusOpenRef.current = false })
      }}
      onFocusCapture={(event) => {
        if (suppressFocusOpenRef.current) return
        const target = event.target
        if (target instanceof HTMLElement && target.matches(':focus-visible')) requestOpen()
      }}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) requestClose(100, false)
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape' && open) {
          event.stopPropagation()
          clearTimers()
          setOpen(false)
          suppressFocusOpenRef.current = true
          requestAnimationFrame(() => {
            document.querySelector<HTMLElement>('.eye-hit')?.focus()
            queueMicrotask(() => { suppressFocusOpenRef.current = false })
          })
        }
      }}
    >
      <EyeShell
        width={216}
        state={snapshot.state}
        severity={snapshot.finding?.severity ?? null}
        cursor={cursor}
        optionsExpanded={open}
        optionsControls="eye-input-launcher"
      />
      <span className="visually-hidden" role="status" aria-live="polite">
        {statusText(snapshot.state, 0)}
      </span>
      {open && trayAvailable && (
        <div
          id="eye-input-launcher"
          className="eye-launcher no-drag"
          role="group"
          aria-label="Analysis inputs"
        >
          <button ref={firstOptionRef} onClick={() => choose('screen')}>Share screen</button>
          <button onClick={() => choose('window')}>Share window</button>
          <button onClick={() => choose('text')}>Text note</button>
          <button onClick={() => choose('voice')}>Voice note</button>
        </div>
      )}
    </div>
  )
}
