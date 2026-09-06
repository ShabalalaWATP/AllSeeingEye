import { useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import {
  fetchReportMethodology,
  type ReportMethodology as Methodology,
} from '@/lib/api/reportMethodology';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { isHttpUrl } from '@/lib/urls';

function ContributionTable({ methodology }: { methodology: Methodology }) {
  if (methodology.contribution_matrix.length === 0) {
    return <p className="text-sm text-muted">No contribution matrix is available.</p>;
  }
  return (
    <div
      role="region"
      aria-label="Evidence contribution matrix"
      // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- Keyboard users need focus to scroll the wide matrix.
      tabIndex={0}
      className="overflow-x-auto rounded border border-line"
    >
      <table className="w-full min-w-[36rem] border-collapse text-left text-xs">
        <caption className="p-3 text-left text-muted">
          Source reliability (rows) × information credibility (columns)
        </caption>
        <thead className="bg-surface-2">
          <tr>
            <th scope="col" className="p-3">
              Reliability
            </th>
            {methodology.credibility_scale.map((item) => (
              <th key={item.grade} scope="col" className="p-3" title={item.label}>
                {item.grade}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {methodology.reliability_scale.map((row) => (
            <tr key={row.grade} className="border-t border-line">
              <th scope="row" className="p-3" title={row.label}>
                {row.grade}
              </th>
              {methodology.credibility_scale.map((column) => (
                <td key={column.grade} className="p-3 text-muted">
                  {methodology.contribution_matrix.find(
                    (cell) => cell.reliability === row.grade && cell.credibility === column.grade,
                  )?.contribution ?? 'Not recorded'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MethodologyBody({ savedMethod }: { savedMethod: string | undefined }) {
  const { data, error, loading, reload } = useScopedResource(fetchReportMethodology);
  if (loading) return <LoadingNote label="Loading evidence methodology" />;
  if (error)
    return (
      <div className="space-y-3">
        <Alert tone="error">{describeError(error)}</Alert>
        <Button variant="secondary" onClick={() => void reload()}>
          Retry methodology
        </Button>
      </div>
    );
  if (!data) return <p className="text-sm text-muted">Evidence methodology is unavailable.</p>;
  return (
    <div className="flex min-w-0 flex-col gap-5">
      <div>
        <h3 className="text-sm font-medium">{data.title}</h3>
        <p className="mt-1 text-xs text-muted">Current method: {data.method_version}</p>
        {savedMethod && savedMethod !== data.method_version && (
          <p className="mt-2 text-xs text-amber">
            This version used {savedMethod}. The current guide does not change its saved assessment.
          </p>
        )}
      </div>
      <dl className="grid gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium">Source reliability</dt>
          <dd className="mt-1 text-xs text-muted">
            The source's record and ability to provide reliable reporting. A to F is separate from
            the information grade.
          </dd>
        </div>
        <div>
          <dt className="text-sm font-medium">Information credibility</dt>
          <dd className="mt-1 text-xs text-muted">
            The assessed credibility of this piece of information, from 1 to 6.
          </dd>
        </div>
        <div>
          <dt className="text-sm font-medium">Likelihood</dt>
          <dd className="mt-1 text-xs text-muted">
            How likely a judgement is to be true, expressed using the probability yardstick. The
            contribution matrix does not calculate it.
          </dd>
        </div>
        <div>
          <dt className="text-sm font-medium">Confidence</dt>
          <dd className="mt-1 text-xs text-muted">
            How sound the basis for a judgement is. The engine applies an information-base ceiling;
            it does not measure every dimension of analytical confidence.
          </dd>
        </div>
      </dl>
      <ContributionTable methodology={data} />
      <section aria-label="Probability yardstick">
        <h3 className="text-sm font-medium">Likelihood vocabulary</h3>
        <p className="mt-1 text-xs text-muted">
          These approximate bands explain the probability terms. They are not a calculated accuracy
          score for this report.
        </p>
        <dl className="mt-3 grid gap-3 text-xs sm:grid-cols-2">
          {data.probability_yardstick.map((band) => (
            <div key={band.probability}>
              <dt className="font-medium">{band.term}</dt>
              <dd className="mt-1 text-muted">{band.range_description}</dd>
            </div>
          ))}
        </dl>
      </section>
      <div className="grid gap-4 sm:grid-cols-2">
        <Scale title="Reliability grades" items={data.reliability_scale} />
        <Scale title="Credibility grades" items={data.credibility_scale} />
      </div>
      <div>
        <h3 className="text-sm font-medium">Confidence limits</h3>
        <ul className="mt-2 list-disc space-y-2 pl-5 text-xs text-muted">
          {data.confidence_rules.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      </div>
      <dl className="space-y-3 text-xs">
        {data.assessment_dimensions.map((dimension) => (
          <div key={dimension.name}>
            <dt className="font-medium">
              {dimension.name} ·{' '}
              {dimension.engine_assessed
                ? 'Assessed by this engine'
                : 'Not assessed by this engine'}
            </dt>
            <dd className="mt-1 text-muted">{dimension.description}</dd>
          </div>
        ))}
      </dl>
      <div>
        <h3 className="text-sm font-medium">Limits of this method</h3>
        <ul className="mt-2 list-disc space-y-2 pl-5 text-xs text-muted">
          {data.limitations.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </div>
      <ul className="space-y-2 text-xs">
        {data.doctrine_references.map((reference) => (
          <li key={reference.url}>
            {isHttpUrl(reference.url) ? (
              <a
                className="text-ember underline underline-offset-4"
                href={reference.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {reference.title}
              </a>
            ) : (
              reference.title
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Scale({
  title,
  items,
}: {
  title: string;
  items: { grade: string | number; label: string }[];
}) {
  return (
    <div>
      <h3 className="text-sm font-medium">{title}</h3>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
        {items.map((item) => (
          <div key={item.grade} className="contents">
            <dt className="font-mono">{item.grade}</dt>
            <dd className="text-muted">{item.label}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function ReportMethodology({ savedMethod }: { savedMethod?: string | undefined }) {
  const [open, setOpen] = useState(false);
  return (
    <details
      className="min-w-0 border-b border-line pb-4"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary className="cursor-pointer py-3 text-sm font-medium">How evidence is weighed</summary>
      {open && (
        <div className="pt-3">
          <MethodologyBody savedMethod={savedMethod} />
        </div>
      )}
    </details>
  );
}
