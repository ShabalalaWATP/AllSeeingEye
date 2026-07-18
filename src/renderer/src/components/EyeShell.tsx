import EvilEye from './EvilEye/EvilEye'
import { isBusy, type GazeTarget } from '../hooks'
import type { CompanionState, Severity } from '../../../shared/types'

interface EyeShellProps {
  size: number
  state: CompanionState
  severity?: Severity | null
  cursor: GazeTarget
  /** When set, the inner eye is clickable and triggers a screen analysis. */
  interactive?: boolean
}

/**
 * The eye with its state-driven presentation. Visual states are applied at
 * the wrapper level (CSS filters and animations) plus shader uniforms, so the
 * WebGL internals stay untouched. The outer ring is the window drag handle;
 * the inner disc is no-drag so clicks and right-clicks work there.
 */
export default function EyeShell({
  size,
  state,
  severity,
  cursor,
  interactive = true
}: EyeShellProps): React.JSX.Element {
  const glowIntensity = state === 'analysing' ? 0.8 : severity === 'high' ? 0.65 : 0.35
  const flameSpeed = state === 'analysing' ? 1.7 : 1.0
  const stateClass = `state-${state}${severity === 'high' ? ' sev-high-pulse' : ''}`

  const onActivate = (): void => {
    if (interactive && !isBusy(state) && state !== 'paused') {
      void window.criticalEye.analyseScreen()
    }
  }

  return (
    <div className="eye-shell drag" style={{ width: size, height: size }}>
      <div
        className={`eye-hit no-drag ${stateClass}`}
        style={{ width: Math.round(size * 0.74), height: Math.round(size * 0.74) }}
        onClick={onActivate}
        role="button"
        aria-label="Analyse this screen"
        title="Click to analyse this screen (Ctrl+Shift+R). Right-click for menu."
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
