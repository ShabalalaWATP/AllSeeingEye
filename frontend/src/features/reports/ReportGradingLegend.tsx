/**
 * A collapsed reading key for the two scales the document uses. It restates public
 * doctrine only; it asserts nothing about this report's own confidence or grades,
 * which are shown where the data records them.
 */
export function ReportGradingLegend() {
  return (
    <details className="report-reader-legend mt-4">
      <summary className="report-reader-legend-summary">How to read the ratings</summary>
      <dl className="report-reader-legend-body">
        <div>
          <dt>Likelihood</dt>
          <dd>
            The UK PHIA probability yardstick. It describes an assessed likelihood, not a measured
            probability.
          </dd>
        </div>
        <div>
          <dt>Analytical confidence</dt>
          <dd>
            Low, moderate or high. It describes how strong and stable the basis for a judgement is,
            separately from how likely the judgement is.
          </dd>
        </div>
        <div>
          <dt>Source grade</dt>
          <dd>
            A letter for source reliability (A to F) and a number for information credibility (1 to
            6). F and 6 mean there were insufficient grounds to judge, not that the reporting was
            false.
          </dd>
        </div>
      </dl>
    </details>
  );
}
