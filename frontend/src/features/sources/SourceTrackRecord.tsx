import { useCallback, useState } from 'react';
import { Link } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { verdictShares } from '@/lib/api/citationVerdicts';
import { describeError } from '@/lib/api/errors';
import { fetchSourceTrackRecord, type SourceTrackRecord } from '@/lib/api/sourceTrackRecord';
import { formatUtc } from '@/lib/format';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

import {
  REVIEW_KIND_LABELS,
  STATUS_LABELS,
  boundText,
  formatCount,
  plural,
  populationText,
} from './trackRecordPresentation';

const STATUSES = ['ready', 'needs_review', 'failed'] as const;

function Heading({ children }: { children: string }) {
  return <h5 className="mt-3 text-xs font-semibold text-text">{children}</h5>;
}

function Facts({ rows }: { rows: [string, number][] }) {
  return (
    <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1">
      {rows.map(([label, value]) => (
        <div key={label} className="contents">
          <dt>{label}</dt>
          <dd className="text-right font-mono text-text">{formatCount(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function Grades({ title, values }: { title: string; values: SourceTrackRecord['reliability'] }) {
  return (
    <div>
      <Heading>{title}</Heading>
      {values.length === 0 ? (
        <p>None frozen.</p>
      ) : (
        <ul className="flex flex-wrap gap-x-4">
          {values.map((row) => (
            <li key={row.value}>{`${row.value}: ${plural(row.items, 'item')}`}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Summary({ record }: { record: SourceTrackRecord }) {
  const { roles } = record;
  return (
    <div className="space-y-1 leading-5">
      <p className="text-text">{populationText(record)}</p>
      <p>{boundText(record)}</p>
      <Heading>Role in citing reports</Heading>
      <Facts
        rows={[
          ['Supporting a key judgement', roles.supporting_judgements],
          ['Contradicting a key judgement', roles.contradicting_judgements],
          ['Items cited elsewhere in the report', roles.items_cited_elsewhere],
          ['Items frozen but not cited', roles.items_not_cited],
        ]}
      />
      <table className="mt-3 w-full text-left">
        <caption className="text-left font-semibold text-text">Saved status</caption>
        <thead>
          <tr>
            <th scope="col" className="font-normal">
              Status
            </th>
            <th scope="col" className="text-right font-normal">
              Citing reports
            </th>
            <th scope="col" className="text-right font-normal">
              Citing judgements
            </th>
          </tr>
        </thead>
        <tbody>
          {STATUSES.map((status) => (
            <tr key={status}>
              <th scope="row" className="font-normal">
                {STATUS_LABELS[status]}
              </th>
              <td className="text-right font-mono text-text">
                {formatCount(record.reports_by_status[status])}
              </td>
              <td className="text-right font-mono text-text">
                {formatCount(record.judgements_by_status[status])}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="grid gap-x-6 sm:grid-cols-2">
        <Grades title="Reliability as frozen" values={record.reliability} />
        <Grades title="Credibility as frozen" values={record.credibility} />
      </div>
    </div>
  );
}

function Entries({ record }: { record: SourceTrackRecord }) {
  if (record.entries.length === 0) return null;
  return (
    <div>
      <Heading>Citing reports</Heading>
      <ul className="divide-y divide-line">
        {record.entries.map((entry) => (
          <li key={entry.report_id} className="py-1.5">
            <Link
              to={`/reports/${entry.report_id}`}
              className="text-ember hover:underline focus-visible:outline-2 focus-visible:outline-ember"
            >
              {entry.title}
            </Link>
            <p>
              {`Version ${entry.version_number} · ${STATUS_LABELS[entry.status]} · saved ${formatUtc(entry.saved_at)} · ${plural(entry.items, 'item')} (${entry.grades.join(', ')}) · supports ${formatCount(entry.supporting_judgements)}, contradicts ${formatCount(entry.contradicting_judgements)} key judgements`}
            </p>
          </li>
        ))}
      </ul>
      <p>{`Showing ${formatCount(record.entries.length)} of ${plural(record.entries_total, 'citing report')}, newest first.`}</p>
    </div>
  );
}

function Verdicts({ verdicts }: { verdicts: SourceTrackRecord['citation_verdicts'] }) {
  return (
    <>
      <p>{verdicts.note}</p>
      {verdicts.available && (
        <>
          <p>
            {`${plural(verdicts.current_verdicts, 'current verdict')} from ${plural(verdicts.reviewers, 'reviewer')} on ${formatCount(verdicts.citations_with_verdicts)} of ${plural(verdicts.citations, 'key-judgement citation')} (${formatCount(verdicts.superseded_verdicts)} superseded).`}
          </p>
          <ul>
            {verdictShares(verdicts, verdicts.current_verdicts).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}

function Reviews({ record }: { record: SourceTrackRecord }) {
  return (
    <div>
      <Heading>Source reviews</Heading>
      {record.reviews.length === 0 ? (
        <p>No reviewer decisions recorded.</p>
      ) : (
        <>
          <ul>
            {record.reviews.map((review) => (
              <li key={`${review.kind}-${review.report_id}-${review.recorded_at}`}>
                {`${REVIEW_KIND_LABELS[review.kind]} ${review.decision} · ${review.team_scoped ? 'Team review' : 'Personal review'} · recorded ${formatUtc(review.recorded_at)}`}
              </li>
            ))}
          </ul>
          <p>{`Showing ${formatCount(record.reviews.length)} of ${plural(record.reviews_total, 'current decision')}.`}</p>
        </>
      )}
      <Heading>Citation verdicts</Heading>
      <Verdicts verdicts={record.citation_verdicts} />
    </div>
  );
}

function TrackRecordPanel({ sourceId, sourceName }: { sourceId: string; sourceName: string }) {
  const loader = useCallback(() => fetchSourceTrackRecord(sourceId), [sourceId]);
  const { data, error, loading, reload } = useScopedResource(loader);
  return (
    <section aria-label={`Track record for ${sourceName}`} className="space-y-2 py-2">
      {loading && !data && <LoadingNote label="Loading track record" />}
      {error !== null && (
        <Alert tone="error">
          {describeError(error)}{' '}
          <Button variant="secondary" onClick={() => void reload()}>
            Retry track record
          </Button>
        </Alert>
      )}
      {data && (
        <>
          <Summary record={data} />
          <Entries record={data} />
          <Reviews record={data} />
        </>
      )}
    </section>
  );
}

/** Read-only and computed on request; nothing loads until the reader opens it. */
export function SourceTrackRecordDetails({
  sourceId,
  sourceName,
}: {
  sourceId: string;
  sourceName: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <details className="text-xs text-muted" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="w-fit cursor-pointer py-2 focus-visible:outline-2 focus-visible:outline-ember">
        Track record
      </summary>
      {open && <TrackRecordPanel sourceId={sourceId} sourceName={sourceName} />}
    </details>
  );
}
