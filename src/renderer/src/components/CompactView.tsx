import { useEffect, useRef } from 'react'
import EyeShell from './EyeShell'
import QuitButton from './QuitButton'
import {
  isBusy,
  prettifyCategory,
  severityClass,
  statusText,
  useElapsed,
  useFitHeight,
  type GazeTarget
} from '../hooks'
import type { StatePayload } from '../../../shared/types'

interface CompactViewProps {
  snapshot: StatePayload
  cursor: GazeTarget
  onFullReview: () => void
}

/** The 520-wide window: eye on the left, content-sized bubble on the right. */
export default function CompactView({
  snapshot,
  cursor,
  onFullReview
}: CompactViewProps): React.JSX.Element {
  const busy = isBusy(snapshot.state)
  const elapsed = useElapsed(snapshot.state === 'analysing')
  const rootRef = useFitHeight<HTMLDivElement>()

  const showPrivacy =
    !snapshot.privacyNoticeDismissed &&
    !snapshot.finding &&
    !snapshot.quickResult &&
    !snapshot.error &&
    !busy

  return (
    <div className="compact-window" ref={rootRef}>
      <QuitButton className="compact-app-quit" />
      <div className="compact-eye">
        <EyeShell
          width={150}
          state={snapshot.state}
          severity={snapshot.finding?.severity ?? null}
          cursor={cursor}
        />
        <div className="status-label drag">{statusText(snapshot.state, elapsed)}</div>
      </div>
      <div className="panel compact-body">
        <div className="panel-drag drag" />
        {showPrivacy ? (
          <PrivacyBlock />
        ) : busy ? (
          <ProgressBlock label={statusText(snapshot.state, elapsed, snapshot.reviewPhase)} />
        ) : snapshot.quickResult ? (
          <QuickResultBlock snapshot={snapshot} onFullReview={onFullReview} />
        ) : snapshot.error ? (
          <ErrorBlock message={snapshot.error.message} />
        ) : snapshot.finding ? (
          <FindingBlock snapshot={snapshot} onFullReview={onFullReview} />
        ) : (
          <HintBlock />
        )}
      </div>
    </div>
  )
}

function PrivacyBlock(): React.JSX.Element {
  const acknowledge = async (): Promise<void> => {
    await window.criticalEye.updatePreferences({ privacyNoticeDismissed: true })
    await window.criticalEye.dismiss()
  }
  return (
    <div className="block no-drag" role="status" aria-live="polite">
      <p className="notice">
        AllSeeingEye only looks when you ask it to. Screenshots are analysed in memory and are not
        saved by this application.
      </p>
      <div className="actions">
        <button className="btn primary" onClick={() => void acknowledge()}>
          Got it
        </button>
      </div>
    </div>
  )
}

function ProgressBlock({ label }: { label: string }): React.JSX.Element {
  return (
    <div className="block no-drag" role="status" aria-live="polite">
      <p className="progress-label">{label}</p>
      <div className="progress-track">
        <div className="progress-glow" />
      </div>
    </div>
  )
}

function ErrorBlock({ message }: { message: string }): React.JSX.Element {
  return (
    <div className="block no-drag">
      <div className="meta-row">
        <span className="chip chip-error">Unable to analyse</span>
        <button
          className="icon-btn"
          onClick={() => void window.criticalEye.dismiss()}
          title="Dismiss"
        >
          ✕
        </button>
      </div>
      <p className="headline">{message}</p>
      <div className="actions">
        <button className="btn" onClick={() => void window.criticalEye.dismiss()}>
          Choose another input
        </button>
      </div>
    </div>
  )
}

function QuickResultBlock({
  snapshot,
  onFullReview
}: {
  snapshot: StatePayload
  onFullReview: () => void
}): React.JSX.Element {
  const resultRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    requestAnimationFrame(() => resultRef.current?.focus())
  }, [snapshot.quickResult?.runId])

  return (
    <div
      ref={resultRef}
      className="block quick-result no-drag"
      tabIndex={-1}
      aria-label="Quick take ready"
    >
      <div className="meta-row">
        <span className="result-kicker">Quick take</span>
        <button
          className="icon-btn"
          onClick={() => void window.criticalEye.dismiss()}
          title="Dismiss"
        >
          ✕
        </button>
      </div>
      <p className="quick-answer selectable" role="status" aria-live="polite">
        {snapshot.quickResult?.answer}
      </p>
      {snapshot.error && (
        <p className="quick-review-error" role="alert">
          Full analysis could not complete: {snapshot.error.message}
        </p>
      )}
      <label className="quick-depth" htmlFor="quick-review-depth">
        <span>Full analysis</span>
        <select
          id="quick-review-depth"
          value={snapshot.reviewDepth}
          disabled={!snapshot.canRunFullReview}
          onChange={(event) => void window.criticalEye.updatePreferences({
            reviewDepth: event.target.value === 'combined' ? 'combined' : 'focused'
          })}
        >
          <option value="focused">Focused expert</option>
          <option value="combined">Combined experts</option>
        </select>
      </label>
      <div className="actions">
        <button
          className="btn primary"
          disabled={!snapshot.canRunFullReview}
          onClick={onFullReview}
        >
          {snapshot.canRunFullReview ? 'Full analysis' : 'Full analysis unavailable'}
        </button>
        <button className="btn subtle" onClick={() => void window.criticalEye.dismiss()}>
          New input
        </button>
      </div>
    </div>
  )
}

function FindingBlock({
  snapshot,
  onFullReview
}: {
  snapshot: StatePayload
  onFullReview: () => void
}): React.JSX.Element {
  const finding = snapshot.finding!
  const allClear = !finding.hasMaterialIssue
  return (
    <div className="block no-drag">
      <div className="meta-row">
        {allClear ? (
          <span className="chip chip-clear">all clear</span>
        ) : (
          <>
            <span className={`sev-dot ${severityClass(finding.severity)}`} />
            <span className="chip">{prettifyCategory(finding.category)}</span>
          </>
        )}
        <button
          className="icon-btn"
          onClick={() => void window.criticalEye.dismiss()}
          title="Dismiss"
        >
          ✕
        </button>
      </div>
      <p className="headline">{finding.headline}</p>
      <div className="actions">
        <button className="btn primary" onClick={onFullReview}>
          Open full review
        </button>
        <button className="btn subtle" onClick={() => void window.criticalEye.dismiss()}>
          New input
        </button>
      </div>
    </div>
  )
}

function HintBlock(): React.JSX.Element {
  return (
    <div className="block no-drag">
      <p className="notice">
        Press <kbd>Ctrl+Shift+R</kbd> or click the eye to analyse this screen.
      </p>
      <div className="actions">
        <button className="btn" onClick={() => void window.criticalEye.dismiss()}>
          Close
        </button>
      </div>
    </div>
  )
}
