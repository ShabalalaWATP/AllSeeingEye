import { useState } from 'react'
import ModeSelector from './ModeSelector'
import { isBusy, statusText, useElapsed } from '../hooks'
import { MAX_TEXT_LENGTH, type StatePayload } from '../../../shared/types'

interface TextAnalysisProps {
  snapshot: StatePayload
}

/**
 * Manual text analysis: the reliable fallback when screen capture is not an
 * option. Ctrl+Enter submits; plain Enter makes a newline.
 */
export default function TextAnalysis({ snapshot }: TextAnalysisProps): React.JSX.Element {
  const [text, setText] = useState('')
  const busy = isBusy(snapshot.state)
  const elapsed = useElapsed(snapshot.state === 'analysing')
  const canSubmit = text.trim().length > 0 && !busy && !snapshot.paused

  const submit = (): void => {
    if (canSubmit) void window.criticalEye.analyseText(text, snapshot.analysisMode)
  }

  return (
    <div className="text-analysis">
      <ModeSelector snapshot={snapshot} />
      <textarea
        className="text-input selectable"
        value={text}
        maxLength={MAX_TEXT_LENGTH}
        placeholder="Paste a proposal, plan, email or argument here…"
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && event.ctrlKey) {
            event.preventDefault()
            submit()
          }
        }}
      />
      <div className="text-footer">
        <span className="counter">
          {text.length.toLocaleString()}/{MAX_TEXT_LENGTH.toLocaleString()}
        </span>
        {busy && <span className="progress-label">{statusText(snapshot.state, elapsed)}</span>}
        <button className="btn primary" disabled={!canSubmit} onClick={submit}>
          Red team this
        </button>
      </div>
      {snapshot.error && (
        <div className="error-banner">
          <p>{snapshot.error.message}</p>
        </div>
      )}
    </div>
  )
}
