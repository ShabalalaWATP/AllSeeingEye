import { isBusy, prettifyCategory, severityClass, statusText, useElapsed } from '../hooks'
import { EXPERT_LABELS, type StatePayload } from '../../../shared/types'

export default function OverallReview({ snapshot }: { snapshot: StatePayload }): React.JSX.Element {
  const busy = isBusy(snapshot.state)
  const elapsed = useElapsed(snapshot.state === 'analysing')
  const finding = snapshot.finding
  const report = snapshot.report

  if (snapshot.error) {
    return <div className="error-banner" role="alert"><p>{snapshot.error.message}</p></div>
  }
  if (busy && !report) {
    return (
      <div className="detail-progress" role="status">
        <p className="progress-label">
          {statusText(snapshot.state, elapsed, snapshot.reviewPhase)}
        </p>
        <div className="progress-track"><div className="progress-glow" /></div>
      </div>
    )
  }
  if (!report || !finding) {
    return <p className="notice">No review yet. Choose Display, Text or Voice to begin.</p>
  }

  return (
    <article className="finding-detail overall-review">
      <div className="result-kicker">Overall review</div>
      <h2 className="detail-headline">{finding.headline}</h2>
      <div className="meta-row">
        <span className={`sev-dot ${severityClass(finding.severity)}`} />
        <span className="chip">{finding.severity}</span>
        <span className="chip">{prettifyCategory(finding.category)}</span>
        <span className="confidence">{Math.round(finding.confidence * 100)}% evidence confidence</span>
      </div>
      <div className="confidence-track">
        <div className="confidence-fill" style={{ width: `${Math.round(finding.confidence * 100)}%` }} />
      </div>

      <section>
        <h3>Subject</h3>
        <p className="selectable">{report.subjectSummary}</p>
      </section>
      {report.focusQuestion && (
        <section className="review-focus">
          <h3>Your question</h3>
          <p className="selectable">{report.focusQuestion}</p>
        </section>
      )}
      <section>
        <h3>Why it matters</h3>
        <p className="selectable">{finding.explanation}</p>
      </section>
      {finding.visibleEvidence && (
        <section>
          <h3>Observed evidence</h3>
          <blockquote className="selectable">{finding.visibleEvidence}</blockquote>
        </section>
      )}
      <section>
        <h3>Recommended action</h3>
        <p className="selectable">{finding.recommendation}</p>
      </section>

      {report.synthesis ? (
        <section className="combined-detail">
          <h3>Across the board</h3>
          {report.synthesis.agreements.length > 0 && <ReviewList title="Agreement" items={report.synthesis.agreements} />}
          {report.synthesis.disagreements.length > 0 && <ReviewList title="Trade-offs or disagreement" items={report.synthesis.disagreements} />}
          {report.synthesis.prioritisedActions.length > 0 && <ReviewList title="Action sequence" items={report.synthesis.prioritisedActions} ordered />}
        </section>
      ) : (
        <p className="coverage-note">A cross-expert synthesis was unnecessary because fewer than two relevant specialists contributed.</p>
      )}

      <section>
        <h3>Review coverage</h3>
        <div className="expert-roster">
          {report.selectedExperts.map((selection) => (
            <span key={selection.expertId} className="expert-chip" title={selection.reason}>
              {EXPERT_LABELS[selection.expertId]}
            </span>
          ))}
        </div>
        <ul className="coverage-reasons">
          {report.selectedExperts.map((selection) => (
            <li key={selection.expertId}>
              <strong>{EXPERT_LABELS[selection.expertId]}:</strong> {selection.reason}
            </li>
          ))}
        </ul>
        <p className="coverage-note">Only these relevant domains were assessed. Unlisted specialists did not receive the artefact.</p>
      </section>
    </article>
  )
}

function ReviewList({
  title,
  items,
  ordered = false
}: { title: string; items: string[]; ordered?: boolean }): React.JSX.Element {
  const children = items.map((item) => <li key={item}>{item}</li>)
  return <div><strong>{title}</strong>{ordered ? <ol>{children}</ol> : <ul>{children}</ul>}</div>
}
