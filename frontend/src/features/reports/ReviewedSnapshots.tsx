import { useCallback, useId, useRef, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { fetchReportFile } from '@/lib/api/reportDocuments';
import { fetchReportMarkdown, type ReportBody } from '@/lib/api/reports';
import {
  AUTHENTICITY_LABELS,
  CREDIBILITY_LABELS,
  RELIABILITY_LABELS,
  createSourceSnapshot,
  fetchSourceSnapshot,
  fetchSourceSnapshots,
  type ReviewedSnapshot,
} from '@/lib/api/sourceReviews';
import { fileNameFor } from '@/lib/download';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { formatUtc } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

type Format = 'pdf' | 'docx' | 'md';
const FORMATS: [Format, string][] = [
  ['pdf', 'PDF'],
  ['docx', 'Word'],
  ['md', 'Markdown'],
];

function SnapshotTable({ snapshot }: { snapshot: ReviewedSnapshot }) {
  const labels = new Map(snapshot.projection.evidence.map((row) => [row.capture_id, row.label]));
  const judgements = new Map(
    snapshot.projection.claims.map((row) => [row.claim_id, row.judgement_id]),
  );
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <caption className="pb-2 text-left text-text">
          Reviewed source assessment frozen {formatUtc(snapshot.created_at)}
        </caption>
        <thead>
          <tr>
            {[
              'Evidence',
              'Judgement',
              'Subject',
              'Reliability',
              'Credibility',
              'Authenticity',
              'Basis',
            ].map((name) => (
              <th key={name} scope="col" className="pr-3 font-medium">
                {name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {snapshot.projection.assessments.map((row) => (
            <tr key={`${row.evidence_id}:${row.claim_id}`} className="border-t border-line">
              <td className="pr-3">{labels.get(row.evidence_id) ?? row.evidence_id}</td>
              <td className="pr-3">{judgements.get(row.claim_id) ?? row.claim_id}</td>
              <td className="pr-3">{row.subject}</td>
              <td className="pr-3">{RELIABILITY_LABELS[row.reliability]}</td>
              <td className="pr-3">{CREDIBILITY_LABELS[row.credibility]}</td>
              <td className="pr-3">
                {row.authenticity ? AUTHENTICITY_LABELS[row.authenticity.status] : 'Not reviewed'}
              </td>
              <td>
                {row.source_revision || row.assertion_revision
                  ? 'Human review'
                  : 'No human review: unassessed default'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Reviewed-assessment snapshots of one exact version. The original frozen report and its
 * exports stay unchanged unless a snapshot is chosen here; nothing is selected silently.
 */
export function ReviewedSnapshots({
  reportId,
  version,
  title,
  judgements,
  canWrite,
  reviewer,
}: {
  reportId: string;
  version: number;
  title: string;
  judgements: ReportBody['key_judgements'];
  canWrite: boolean;
  reviewer: (id: string) => string;
}) {
  const id = useId();
  const loader = useCallback(() => fetchSourceSnapshots(reportId, version), [reportId, version]);
  const list = useScopedResource(loader);
  const [subjects, setSubjects] = useState<Record<string, string>>({});
  const [announcement, setAnnouncement] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<{ id: string; snapshot: ReviewedSnapshot } | null>(null);
  const [viewError, setViewError] = useState<string | null>(null);
  const latest = useRef<string | null>(null);
  const create = useAsyncAction(async () => {
    setAnnouncement('');
    const trimmed = Object.fromEntries(
      judgements.map((row) => [row.id, (subjects[row.id] ?? '').trim()]),
    );
    await createSourceSnapshot(reportId, version, trimmed);
    await list.refresh();
    setAnnouncement('Snapshot created. Select it to view or export the report with it.');
  });
  const choose = async (snapshotId: string | null) => {
    latest.current = snapshotId;
    setSelected(snapshotId);
    setView(null);
    setViewError(null);
    if (!snapshotId) return;
    try {
      const snapshot = await fetchSourceSnapshot(reportId, version, snapshotId);
      // A slower response for an earlier choice never replaces the current one.
      if (latest.current === snapshotId) setView({ id: snapshotId, snapshot });
    } catch (caught) {
      if (latest.current === snapshotId)
        setViewError(`This snapshot is unavailable: ${describeError(caught)}`);
    }
  };
  const download = useAsyncAction(async (format: Format) => {
    if (!view) return;
    const name = `${title}-v${String(version)}-reviewed`;
    if (format === 'md') {
      const file = await fetchReportMarkdown(reportId, version, view.id);
      saveBinaryFile(file.filename ?? fileNameFor(name, 'md'), file.blob);
    } else {
      const blob = await fetchReportFile(reportId, version, format, view.id);
      saveBinaryFile(fileNameFor(name, format), blob);
    }
  });
  const rows = list.data?.snapshots ?? [];
  const full = list.data !== null && rows.length >= list.data.limit;
  const ready = judgements.every((row) => (subjects[row.id] ?? '').trim());
  return (
    <section aria-label="Reviewed source snapshots" className="space-y-3 text-xs text-muted">
      <h2 className="text-base font-semibold text-text">Reviewed source snapshots</h2>
      <p>
        A snapshot freezes the current human source reviews for this exact version. The original
        frozen report, grading, likelihood and exports are unchanged unless you select a snapshot
        here.
      </p>
      {list.loading && <LoadingNote label="Loading reviewed snapshots" />}
      {list.error && (
        <Alert tone="warning">
          Reviewed snapshots are unavailable: {describeError(list.error)}
        </Alert>
      )}
      {list.data && (
        <>
          {rows.length === 0 && (
            <p>
              No reviewed snapshots for version {version}. This page and its exports use the
              original frozen assessment.
            </p>
          )}
          <div role="radiogroup" aria-label="Source assessment to view" className="space-y-1">
            <label className="flex items-center gap-2 text-text">
              <input
                type="radio"
                name={`${id}-snapshot`}
                checked={selected === null}
                onChange={() => void choose(null)}
              />
              Original frozen assessment (no snapshot)
            </label>
            {rows.map((row) => (
              <label key={row.id} className="flex items-center gap-2 text-text">
                <input
                  type="radio"
                  name={`${id}-snapshot`}
                  checked={selected === row.id}
                  onChange={() => void choose(row.id)}
                />
                {`Snapshot ${formatUtc(row.created_at)} by ${reviewer(row.authored_by)} · ${String(row.decisions)} reviewer decision${row.decisions === 1 ? '' : 's'} · ${Object.entries(
                  row.subjects,
                )
                  .map(([key, value]) => `${key}: ${value}`)
                  .join(', ')}`}
              </label>
            ))}
          </div>
          {full && <p>This version has reached its {list.data.limit}-snapshot limit.</p>}
          {canWrite && !full && (
            <form
              className="space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                void create.run();
              }}
            >
              {judgements.map((row) => (
                <label key={row.id} className="block" htmlFor={`${id}-${row.id}`}>
                  Subject area for {row.id}
                  <input
                    id={`${id}-${row.id}`}
                    className="mt-1 w-full rounded border border-line bg-surface p-2 text-text"
                    maxLength={200}
                    value={subjects[row.id] ?? ''}
                    onChange={(event) => setSubjects({ ...subjects, [row.id]: event.target.value })}
                  />
                </label>
              ))}
              {create.error && <Alert tone="error">{describeError(create.error)}</Alert>}
              <Button type="submit" variant="secondary" busy={create.busy} disabled={!ready}>
                Create reviewed snapshot
              </Button>
            </form>
          )}
          <p role="status" className="text-text">
            {announcement}
          </p>
        </>
      )}
      {viewError && <Alert tone="error">{viewError}</Alert>}
      {selected && !view && !viewError && <LoadingNote label="Loading snapshot" />}
      {view && (
        <>
          <SnapshotTable snapshot={view.snapshot} />
          {download.error && <Alert tone="error">{describeError(download.error)}</Alert>}
          <div className="flex flex-wrap gap-2">
            {FORMATS.map(([format, label]) => (
              <Button
                key={format}
                variant="secondary"
                busy={download.busy}
                onClick={() => void download.run(format)}
              >
                {`Export ${label} with this snapshot`}
              </Button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
