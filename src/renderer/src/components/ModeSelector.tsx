import { ANALYSIS_MODES, type AnalysisMode, type StatePayload } from '../../../shared/types'

const MODE_LABELS: Record<AnalysisMode, string> = {
  general: 'General',
  strategy: 'Strategy',
  security: 'Security',
  writing: 'Writing',
  delivery: 'Delivery'
}

interface ModeSelectorProps {
  snapshot: StatePayload
}

/** Persisted analysis mode; each mode adds a focused prompt addendum. */
export default function ModeSelector({ snapshot }: ModeSelectorProps): React.JSX.Element {
  return (
    <div className="mode-selector" role="radiogroup" aria-label="Analysis mode">
      {ANALYSIS_MODES.map((mode) => (
        <button
          key={mode}
          role="radio"
          aria-checked={snapshot.analysisMode === mode}
          className={`mode-pill ${snapshot.analysisMode === mode ? 'active' : ''}`}
          onClick={() => void window.criticalEye.updatePreferences({ mode })}
        >
          {MODE_LABELS[mode]}
        </button>
      ))}
    </div>
  )
}
