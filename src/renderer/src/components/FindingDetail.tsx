import ModeSelector from './ModeSelector'
import { isBusy, prettifyCategory, severityClass, statusText, useElapsed } from '../hooks'
import type { StatePayload } from '../../../shared/types'

interface FindingDetailProps {
  snapshot: StatePayload
}

export default function FindingDetail({ snapshot }: FindingDetailProps): React.JSX.Element {
  const busy = isBusy(snapshot.state)
  const elapsed = useElapsed(snapshot.state === 'analysing')
  const finding = snapshot.finding

  return (
    <div className="finding-detail">
      <ModeSelector snapshot={snapshot} />

      {snapshot.error && (
        <div className="error-banner">
          <p>{snapshot.error.message}</p>
        </div>
      )}

      {busy ? (
        <div className="detail-progress">
          <p className="progress-label">{statusText(snapshot.state, elapsed)}</p>
          <div className="progress-track">
            <div className="progress-glow" />
          </div>
        </div>
      ) : finding ? (
        <>
          <h2 className="detail-headline">{finding.headline}</h2>
          <div className="meta-row">
            <span className={`sev-dot ${severityClass(finding.severity)}`} />
            <span className="chip">{finding.severity}</span>
            <span className="chip">{prettifyCategory(finding.category)}</span>
            <span className="confidence" title="Model confidence">
              {Math.round(finding.confidence * 100)}% confident
            </span>
          </div>
          <div className="confidence-track">
            <div
              className="confidence-fill"
              style={{ width: `${Math.round(finding.confidence * 100)}%` }}
            />
          </div>

          <section>
            <h3>Explanation</h3>
            <p className="selectable">{finding.explanation}</p>
          </section>
          {finding.visibleEvidence && (
            <section>
              <h3>Visible evidence</h3>
              <blockquote className="selectable">{finding.visibleEvidence}</blockquote>
            </section>
          )}
          <section>
            <h3>Recommended action</h3>
            <p className="selectable">{finding.recommendation}</p>
          </section>
        </>
      ) : (
        !snapshot.error && (
          <p className="notice">
            No analysis yet. Press <kbd>Ctrl+Shift+R</kbd>, click the eye, or paste text into the
            Text tab.
          </p>
        )
      )}

      <div className="actions">
        <button
          className="btn primary"
          disabled={busy || snapshot.paused}
          onClick={() => void window.criticalEye.analyseScreen()}
        >
          Analyse this screen again
        </button>
      </div>
    </div>
  )
}
