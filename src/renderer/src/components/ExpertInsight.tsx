import {
  EXPERT_LABELS,
  type ExpertAnalysis,
  type ExpertSelection
} from '../../../shared/types'
import { prettifyCategory, severityClass } from '../hooks'

export default function ExpertInsight({
  analysis,
  selection
}: {
  analysis: ExpertAnalysis
  selection: ExpertSelection | undefined
}): React.JSX.Element {
  const needsContext = analysis.applicability === 'insufficient_context'
  return (
    <article className="expert-insight">
      <div className="result-kicker">Specialist insight</div>
      <h2>{EXPERT_LABELS[analysis.expertId]}</h2>
      {selection && <p className="route-reason selectable">{selection.reason}</p>}
      <p className="expert-summary selectable">{analysis.summary}</p>

      {needsContext && <div className="context-banner">Needs context before this specialist can reach a conclusion.</div>}
      {!needsContext && analysis.findings.length === 0 && (
        <p className="notice">No material issue was found within this specialist’s remit.</p>
      )}

      {analysis.findings.map((finding) => (
        <section className="expert-finding" key={`${analysis.expertId}-${finding.headline}`}>
          <div className="meta-row">
            <span className={`sev-dot ${severityClass(finding.severity)}`} />
            <span className="chip">{finding.severity}</span>
            <span className="chip">{prettifyCategory(finding.category)}</span>
          </div>
          <h3>{finding.headline}</h3>
          <p className="selectable">{finding.explanation}</p>
          {finding.visibleEvidence && <blockquote className="selectable">{finding.visibleEvidence}</blockquote>}
          <div className="insight-row"><strong>Recommendation</strong><p>{finding.recommendation}</p></div>
          <div className="insight-row"><strong>Validate next</strong><p>{finding.validationNeeded}</p></div>
          <small>Evidence strength: {finding.evidenceStrength}. Confidence: {Math.round(finding.confidence * 100)}%.</small>
          {finding.sourceRefs.length > 0 && <small>Knowledge sources: {finding.sourceRefs.join(', ')}</small>}
        </section>
      ))}

      {analysis.assumptions.length > 0 && <InsightList title="Assumptions" items={analysis.assumptions} />}
      {analysis.questions.length > 0 && <InsightList title="Questions to resolve" items={analysis.questions} />}
      <footer className="expert-disclaimer">Pack {analysis.packVersion}. {analysis.disclaimer}</footer>
    </article>
  )
}

function InsightList({ title, items }: { title: string; items: string[] }): React.JSX.Element {
  return <section><h3>{title}</h3><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></section>
}
