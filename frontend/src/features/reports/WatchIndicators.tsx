import { useId, useState } from 'react';
import { useNavigate } from 'react-router';

import { prepareReportWatch, reportWatchScope } from '@/lib/alertRuleDraft';
import type { Report, ReportVersion } from '@/lib/api/reports';

/** Each judgement's "Watch for" indicators, with an explicit hand-off to an alert rule draft. */
export function WatchIndicators({
  report,
  version,
}: {
  report: Report['report'];
  version: ReportVersion;
}) {
  const navigate = useNavigate();
  const headingId = useId();
  const [error, setError] = useState<string | null>(null);
  const judgements = version.body.key_judgements
    .map((judgement, index) => ({ judgement, number: index + 1 }))
    .filter(({ judgement }) => judgement.indicators.length > 0);
  if (judgements.length === 0) return null;
  const draft = (judgement: (typeof judgements)[number]) => {
    try {
      prepareReportWatch({
        source: {
          reportId: report.id,
          version: version.number,
          title: report.title,
          judgementNumber: judgement.number,
          statement: judgement.judgement.statement,
          teamId: report.team_id ?? null,
        },
        indicators: judgement.judgement.indicators,
        ...reportWatchScope(report.scope),
      });
      void navigate('/warning');
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'This draft could not be prepared.');
    }
  };
  return (
    <section
      aria-labelledby={headingId}
      className="report-reader-print-hide mt-6 space-y-3 rounded-card border border-line p-4 text-sm"
    >
      <h2 id={headingId} className="text-base font-semibold">
        Watch for these indicators
      </h2>
      <p className="text-xs leading-5 text-muted">
        Turn a judgement&apos;s indicators into an editable alert rule draft. Alert rules match
        keywords literally in new items; they do not check whether the indicator has occurred.
        Nothing is saved until you add the rule, and this report version does not change.
      </p>
      <ul className="space-y-3">
        {judgements.map((item) => (
          <li key={item.judgement.id} className="space-y-1">
            <p className="font-medium">Judgement {item.number}</p>
            <ul className="list-disc pl-5 text-muted">
              {item.judgement.indicators.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
            <button
              type="button"
              onClick={() => draft(item)}
              className="min-h-10 rounded-md border border-cyan/40 px-3 text-sm text-text hover:bg-cyan/10"
            >
              Draft an alert rule from judgement {item.number}
            </button>
          </li>
        ))}
      </ul>
      {error && (
        <p role="alert" className="text-sm text-critical">
          {error}
        </p>
      )}
    </section>
  );
}
