import EvilEye from './EvilEye/EvilEye'
import { isBusy, type GazeTarget } from '../hooks'
import type { CompanionState, Severity } from '../../../shared/types'

interface EyeShellProps {
  /** Overall width; the eye is a wide shape about half as tall as it is wide. */
  width: number
  state: CompanionState
  severity?: Severity | null
  cursor: GazeTarget
  /** When set, the inner eye is clickable and triggers a screen analysis. */
  interactive?: boolean
}

/**
 * The eye with its state-driven presentation. Visual states are applied at
 * the wrapper level (CSS filters and animations) plus shader uniforms, so the
 * WebGL internals stay untouched.
 *
 * Dragging: the eye itself is grabbable anywhere. CSS app-region drag would
 * swallow clicks, so the eye uses manual dragging through the main process; a
 * release that never moved past the threshold counts as a click and triggers
 * analysis. The (invisible) outer ring stays an OS drag region as a backup.
 */
export default function EyeShell({
  width,
  state,
  severity,
  cursor,
  interactive = true
}: EyeShellProps): React.JSX.Element {
  const glowIntensity = state === 'analysing' ? 0.8 : severity === 'high' ? 0.65 : 0.35
  const flameSpeed = state === 'analysing' ? 1.7 : 1.0
  const stateClass = `state-${state}${severity === 'high' ? ' sev-high-pulse' : ''}`

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>): void => {
    if (event.button !== 0) return
    // Guarantees the pointerup lands here even if the pointer briefly leaves.
    event.currentTarget.setPointerCapture(event.pointerId)
    void window.criticalEye.dragBegin()
  }

  const onPointerUp = async (event: React.PointerEvent<HTMLDivElement>): Promise<void> => {
    if (event.button !== 0) return
    const { wasClick } = await window.criticalEye.dragEnd()
    if (wasClick && interactive && !isBusy(state) && state !== 'paused') {
      void window.criticalEye.analyseScreen()
    }
  }

  return (
    <div className="eye-shell drag" style={{ width, height: Math.round(width * 0.55) }}>
      <div
        className={`eye-hit no-drag ${stateClass}`}
        style={{ width: Math.round(width * 0.94), height: Math.round(width * 0.48) }}
        onPointerDown={onPointerDown}
        onPointerUp={(event) => void onPointerUp(event)}
        role="button"
        aria-label="Analyse this screen"
        title="Drag to move. Click to analyse this screen (Ctrl+Shift+R). Right-click for menu."
      >
        <EvilEye
          glowIntensity={glowIntensity}
          flameSpeed={flameSpeed}
          targetX={cursor.tx}
          targetY={cursor.ty}
        />
      </div>
    </div>
  )
}
