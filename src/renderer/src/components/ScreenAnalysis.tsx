import { useEffect, useRef, useState } from 'react'
import { isBusy, statusText, useElapsed } from '../hooks'
import {
  MAX_FOCUS_QUESTION_LENGTH,
  type CaptureSourceBatch,
  type CaptureSourceKind,
  type CaptureTarget,
  type StatePayload
} from '../../../shared/types'

export default function ScreenAnalysis({
  snapshot,
  requestedKind
}: {
  snapshot: StatePayload
  requestedKind: CaptureSourceKind
}): React.JSX.Element {
  const [batch, setBatch] = useState<CaptureSourceBatch | null>(null)
  const [selectedToken, setSelectedToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [batchExpired, setBatchExpired] = useState(false)
  const [pickerError, setPickerError] = useState('')
  const [question, setQuestion] = useState(snapshot.report?.focusQuestion ?? '')
  const requestRef = useRef(0)
  const firstSourceRef = useRef<HTMLButtonElement>(null)
  const busy = isBusy(snapshot.state)
  const elapsed = useElapsed(snapshot.state === 'analysing')

  const load = async (): Promise<void> => {
    const request = requestRef.current + 1
    requestRef.current = request
    setLoading(true)
    setBatch(null)
    setBatchExpired(false)
    setPickerError('')
    setSelectedToken(null)
    try {
      const next = await window.criticalEye.listCaptureSources(requestedKind)
      if (requestRef.current !== request) return
      if (!next) throw new Error('Source enumeration was rejected.')
      setBatch(next)
    } catch {
      if (requestRef.current !== request) return
      setBatch(null)
      setPickerError('Could not list capture sources. Try refreshing the picker.')
    } finally {
      if (requestRef.current === request) setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    return () => { requestRef.current += 1 }
  }, [requestedKind])

  useEffect(() => {
    if (!batch || batch.sources.length === 0) return
    requestAnimationFrame(() => firstSourceRef.current?.focus())
  }, [batch])

  useEffect(() => {
    if (!batch) return
    const expire = (): void => {
      setBatchExpired(true)
      setSelectedToken(null)
      setPickerError('Selection expired. Refresh and choose again.')
    }
    const remaining = batch.expiresAt - Date.now()
    if (remaining <= 0) {
      expire()
      return
    }
    const timer = setTimeout(expire, remaining)
    return () => clearTimeout(timer)
  }, [batch])

  const target: CaptureTarget | null = selectedToken && batch && !batchExpired
    ? { type: 'selected', batchId: batch.batchId, token: selectedToken }
    : null

  const submit = (): void => {
    if (!busy && !snapshot.paused && target) {
      void window.criticalEye.analyseScreen(question.trim(), snapshot.reviewDepth, target)
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
    <div className="screen-analysis">
      <div className="composer-heading">
        <div>
          <span className="result-kicker">{requestedKind === 'display' ? 'Share screen' : 'Share window'}</span>
          <h2>Choose one {requestedKind === 'display' ? 'screen' : 'window'}</h2>
        </div>
        <button className="btn subtle" onClick={() => void load()} disabled={loading}>Refresh</button>
      </div>
      {!loading && batch && !batchExpired && !selectedToken && batch.sources.length > 0 && (
        <p className="selection-prompt" role="status">
          Choose one {requestedKind === 'display' ? 'screen' : 'window'} to continue.
        </p>
      )}
      <div className="source-grid" aria-busy={loading}>
        {loading && <p className="notice">Looking for {requestedKind === 'display' ? 'screens' : 'application windows'}…</p>}
        {!loading && batch?.sources.map((source, index) => (
          <button
            ref={index === 0 ? firstSourceRef : undefined}
            className={`source-card ${source.token === selectedToken ? 'selected' : ''}`}
            key={source.token}
            onClick={() => setSelectedToken(source.token)}
            aria-pressed={source.token === selectedToken}
            title={source.label}
            disabled={batchExpired}
          >
            {source.previewDataUrl
              ? <img src={source.previewDataUrl} alt="" />
              : <span className="source-placeholder">Preview unavailable</span>}
            <span>{source.label}</span>
          </button>
        ))}
        {!loading && batch && batch.sources.length === 0 && <p className="notice">No available sources were found.</p>}
      </div>
      {pickerError && <div className="error-banner" role="alert"><p>{pickerError}</p></div>}

      <details className="focus-disclosure">
        <summary>Ask something specific</summary>
        <label className="field-label" htmlFor="screen-focus">Optional focus question</label>
        <textarea
          id="screen-focus"
          className="focus-input selectable"
          value={question}
          maxLength={MAX_FOCUS_QUESTION_LENGTH}
          placeholder="For example: Is the rollback plan credible?"
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && event.ctrlKey) {
              event.preventDefault()
              submit()
            }
          }}
        />
      </details>
      <p className="capture-scope">
        Only the selected {requestedKind === 'display' ? 'screen' : 'window'} is sent when you continue. Previews stay local.
      </p>
      <div className="text-footer">
        <button className="btn primary" disabled={busy || snapshot.paused || !target} onClick={submit}>
          Get a quick take
        </button>
      </div>
      {snapshot.error && <div className="error-banner" role="alert"><p>{snapshot.error.message}</p></div>}
    </div>
  )
}
