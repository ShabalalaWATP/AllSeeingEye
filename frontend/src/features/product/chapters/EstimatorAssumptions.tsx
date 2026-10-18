/**
 * The estimator's assumptions, generated from the dated figures in costModel.ts, so
 * every constant is listed with its source and the date it was checked.
 */
import { formatCheckedOn, listAssumptions } from '../content/costing';

export function EstimatorAssumptions() {
  return (
    <details className="estimator-assumptions">
      <summary>Assumptions, sources and checked dates</summary>
      <p>
        An estimate, not a quote. Hosting and model costs are paid to your own providers; enter your
        provider&rsquo;s prices for a closer figure.
      </p>
      <ul>
        {listAssumptions().map((entry) => (
          <li key={entry.id}>
            <span className="estimator-assumption-label">{entry.label}:</span> {entry.value}.{' '}
            <span className="estimator-assumption-source">
              Source: {entry.source}. Checked{' '}
              <time dateTime={entry.checkedOn}>{formatCheckedOn(entry.checkedOn)}</time>.
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}
