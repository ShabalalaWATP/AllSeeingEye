import { REVIEW_DEPTHS, type ReviewDepth, type StatePayload } from '../../../shared/types'

const LABELS: Record<ReviewDepth, { title: string; hint: string }> = {
  focused: { title: 'Focused', hint: 'One best-fit expert' },
  combined: { title: 'Combined', hint: 'Relevant experts, synthesised' }
}

export default function DepthSelector({ snapshot }: { snapshot: StatePayload }): React.JSX.Element {
  return (
    <fieldset className="depth-selector">
      <legend>Review depth</legend>
      {REVIEW_DEPTHS.map((depth) => (
        <label key={depth} className={snapshot.reviewDepth === depth ? 'active' : ''}>
          <input
            type="radio"
            name="review-depth"
            value={depth}
            checked={snapshot.reviewDepth === depth}
            onChange={() => void window.criticalEye.updatePreferences({ reviewDepth: depth })}
          />
          <span>
            <strong>{LABELS[depth].title}</strong>
            <small>{LABELS[depth].hint}</small>
          </span>
        </label>
      ))}
    </fieldset>
  )
}
