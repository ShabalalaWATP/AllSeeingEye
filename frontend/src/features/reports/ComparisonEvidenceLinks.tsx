import type { ComparisonSide } from '@/lib/api/annotationComparisons';
export const comparisonReportHref = (side: ComparisonSide) =>
  `/reports/${encodeURIComponent(side.report_id)}?version=${side.version_number}`;
export function ComparisonEvidenceLinks({
  side,
  labels,
  name,
}: {
  side: ComparisonSide;
  labels: string[];
  name: string;
}) {
  return (
    <span className="inline-flex flex-wrap gap-2">
      {[...new Set(labels)].map((label) =>
        side.evidence.some((item) => item.label === label) ? (
          <a
            className="text-ember underline"
            key={label}
            href={`${comparisonReportHref(side)}#evidence-${encodeURIComponent(label)}`}
            aria-label={`${name}: view evidence ${label} in version ${side.version_number}`}
          >
            {label}
          </a>
        ) : (
          <span key={label}>{label} (not captured on this side)</span>
        ),
      )}
    </span>
  );
}
