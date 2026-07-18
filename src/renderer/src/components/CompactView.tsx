import { useEffect } from 'react'
import EyeShell from './EyeShell'
import {
  isBusy,
  prettifyCategory,
  severityClass,
  statusText,
  useElapsed,
  type GazeTarget
} from '../hooks'
import type { StatePayload } from '../../../shared/types'

interface CompactViewProps {
  snapshot: StatePayload
  cursor: GazeTarget
}

const NO_ISSUE_AUTO_DISMISS_MS = 8000

/** The 520x200 window: eye on the left, one-line content on the right. */
export default function CompactView({ snapshot, cursor }: CompactViewProps): React.JSX.Element {
  const busy = isBusy(snapshot.state)
  const elapsed = useElapsed(snapshot.state === 'analysing')

  // A calm all-clear does not deserve to hang around.
  useEffect(() => {
    if (snapshot.state !== 'no_issue') return
    const id = setTimeout(() => void window.criticalEye.dismiss(), NO_ISSUE_AUTO_DISMISS_MS)
    return () => clearTimeout(id)
  }, [snapshot.state])

  const showPrivacy =
    !snapshot.privacyNoticeDismissed && !snapshot.finding && !snapshot.error && !busy

  return (
    <div className="compact-window">
      <div className="compact-eye">
        <EyeShell
          size={130}
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
          <ProgressBlock label={statusText(snapshot.state, elapsed)} />
        ) : snapshot.error ? (
          <ErrorBlock message={snapshot.error.message} />
        ) : snapshot.finding ? (
          <FindingBlock snapshot={snapshot} />
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
    <div className="block no-drag">
      <p className="notice">
        Critical Eye only looks when you ask it to. Screenshots are analysed in memory and are not
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
    <div className="block no-drag">
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
        <button className="btn" onClick={() => void window.criticalEye.analyseScreen()}>
          Try again
        </button>
      </div>
    </div>
  )
}

function FindingBlock({ snapshot }: { snapshot: StatePayload }): React.JSX.Element {
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
        {!allClear && (
          <button
            className="btn primary"
            onClick={() => void window.criticalEye.setWindowMode('expanded')}
          >
            Expand
          </button>
        )}
        <button className="btn" onClick={() => void window.criticalEye.analyseScreen()}>
          Reanalyse
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
