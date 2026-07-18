import { useState } from 'react'
import { isBusy, statusText, useElapsed } from '../hooks'
import {
  MAX_FOCUS_QUESTION_LENGTH,
  MAX_TEXT_LENGTH,
  type StatePayload
} from '../../../shared/types'

interface TextAnalysisProps {
  snapshot: StatePayload
}

/**
 * Manual text analysis: the reliable fallback when screen capture is not an
 * option. Ctrl+Enter submits; plain Enter makes a newline.
 */
export default function TextAnalysis({ snapshot }: TextAnalysisProps): React.JSX.Element {
  const [text, setText] = useState('')
  const [question, setQuestion] = useState('')
  const busy = isBusy(snapshot.state)
  const elapsed = useElapsed(snapshot.state === 'analysing')
  const canSubmit = text.trim().length > 0 && !busy && !snapshot.paused

  const submit = (): void => {
    if (canSubmit) {
      void window.criticalEye.analyseText(
        text,
        snapshot.analysisMode,
        question.trim(),
        snapshot.reviewDepth
      )
    }
  }

  if (busy) {
    return (
      <div className="input-progress" role="status" aria-live="polite">
        <p>{statusText(snapshot.state, elapsed, snapshot.reviewPhase)}</p>
        <div className="progress-track"><div className="progress-glow" /></div>
      </div>
    )
  }

  return (
    <div className="text-analysis">
      <div className="composer-heading">
        <div>
          <span className="result-kicker">Text input</span>
          <h2>What would you like a quick take on?</h2>
        </div>
      </div>
      <label className="field-label" htmlFor="text-artefact">Text or question</label>
      <textarea
        id="text-artefact"
        className="text-input selectable"
        autoFocus
        value={text}
        maxLength={MAX_TEXT_LENGTH}
        placeholder="Type or paste what you want a quick take on…"
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && event.ctrlKey) {
            event.preventDefault()
            submit()
          }
        }}
      />
      <details className="focus-disclosure">
        <summary>Ask something specific</summary>
        <label className="field-label" htmlFor="text-focus">Optional focus question</label>
        <input
          id="text-focus"
          className="single-line-input selectable"
          value={question}
          maxLength={MAX_FOCUS_QUESTION_LENGTH}
          placeholder="For example: What assumption is weakest?"
          onChange={(event) => setQuestion(event.target.value)}
        />
      </details>
      <div className="text-footer">
        {text.length >= MAX_TEXT_LENGTH * 0.8 && (
          <span className="counter">
            {text.length.toLocaleString()}/{MAX_TEXT_LENGTH.toLocaleString()}
          </span>
        )}
        <button className="btn primary" disabled={!canSubmit} onClick={submit}>
          Get a quick take
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
