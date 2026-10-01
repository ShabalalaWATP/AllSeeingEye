import { useId, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError, isApiError } from '@/lib/api/errors';
import type { EvidenceItem, ReportBody } from '@/lib/api/reports';
import {
  AUTHENTICITY_LABELS,
  CREDIBILITY_LABELS,
  MAX_REVIEW_REVISIONS,
  RELIABILITY_LABELS,
  fetchSourceReviewHistory,
  recordSourceReview,
  type SourceReviewInput,
  type SourceReviewKind,
  type SourceReviewRevision,
} from '@/lib/api/sourceReviews';
import { formatUtc } from '@/lib/format';

import { EMPTY_DRAFT, SourceReviewForm, type ReviewDraft } from './SourceReviewForm';

type KeyJudgement = ReportBody['key_judgements'][number];

export interface SourceReviewContext {
  reportId: string;
  version: number;
  judgements: readonly KeyJudgement[];
  /** Write authority on the report's scope; the server re-checks every request. */
  canWrite: boolean;
  scopeLabel: string;
  reviewer: (id: string) => string;
}

const KINDS: [SourceReviewKind, string][] = [
  ['reliability', 'Reliability'],
  ['credibility', 'Credibility'],
  ['authenticity', 'Authenticity'],
];

function grade(row: SourceReviewRevision): string {
  if (row.reliability) return RELIABILITY_LABELS[row.reliability];
  if (row.credibility) return CREDIBILITY_LABELS[row.credibility];
  if (row.authenticity) return `Authenticity ${AUTHENTICITY_LABELS[row.authenticity.status]}`;
  return 'Recorded';
}

function scopeText(kind: SourceReviewKind, item: EvidenceItem, judgement: string, ctx: string) {
  if (kind === 'reliability')
    return `Reliability of ${item.source_id} on this subject. It applies across this ${ctx} scope, wherever this source is reviewed for the same subject.`;
  if (kind === 'credibility')
    return `Credibility of ${item.label} for ${judgement} only. It does not grade the source for other claims or captures.`;
  return `Authenticity of capture ${item.label} and its issuer ${item.source_id}, in this saved version only.`;
}

function History({
  rows,
  reviewer,
}: {
  rows: SourceReviewRevision[];
  reviewer: (id: string) => string;
}) {
  if (rows.length === 0) return <p>No human reviews recorded for this target.</p>;
  return (
    <ol className="space-y-2" aria-label="Review history">
      {rows.map((row) => (
        <li key={row.review.id} className="border-l-2 border-line pl-2">
          <p className="text-text">
            {`Revision ${String(row.number)} · ${grade(row)} · ${reviewer(row.review.assessor_id)} · ${formatUtc(row.review.recorded_at)}`}
            {row.number === rows.length ? ' · Current' : ''}
          </p>
          <p className="whitespace-pre-wrap">{row.review.basis}</p>
          {row.expertise_basis && <p>Expertise basis: {row.expertise_basis}</p>}
          {row.review.policy_note && <p>Policy note: {row.review.policy_note}</p>}
        </li>
      ))}
    </ol>
  );
}

/** Human reliability, credibility or authenticity reviews of one frozen evidence item. */
export function SourceReviewPanel({
  item,
  context,
}: {
  item: EvidenceItem;
  context: SourceReviewContext;
}) {
  const id = useId();
  const citing = context.judgements.filter(
    (row) =>
      row.supporting_evidence.includes(item.label) ||
      row.contradicting_evidence.includes(item.label),
  );
  const [judgementId, setJudgementId] = useState(citing[0]?.id ?? '');
  const [kind, setKind] = useState<SourceReviewKind>('reliability');
  const [subject, setSubject] = useState('');
  const [loaded, setLoaded] = useState<{ key: string; rows: SourceReviewRevision[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [draft, setDraft] = useState<ReviewDraft>(EMPTY_DRAFT);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ message: string; stale: boolean } | null>(null);
  const [announcement, setAnnouncement] = useState('');
  const target = { label: item.label, judgement_id: judgementId, subject: subject.trim(), kind };
  const key = JSON.stringify(target);
  const history = loaded?.key === key ? loaded.rows : null;

  const load = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const rows = await fetchSourceReviewHistory(context.reportId, context.version, target);
      setLoaded({ key, rows });
      setError(null);
    } catch (caught) {
      setLoaded(null);
      setLoadError(describeError(caught));
    } finally {
      setLoading(false);
    }
  };
  const submit = async () => {
    if (!history || busy) return;
    setBusy(true);
    setError(null);
    setAnnouncement('');
    const body: SourceReviewInput = {
      ...target,
      basis: draft.basis.trim(),
      previous_id: history.at(-1)?.review.id ?? null,
      ...(kind === 'reliability' && draft.reliability ? { reliability: draft.reliability } : {}),
      ...(kind === 'reliability' && draft.expertiseBasis.trim()
        ? { expertise_basis: draft.expertiseBasis.trim() }
        : {}),
      ...(kind === 'credibility' && draft.credibility ? { credibility: draft.credibility } : {}),
      ...(kind === 'authenticity' && draft.authenticity
        ? { authenticity: draft.authenticity }
        : {}),
      ...(draft.policyNote.trim() ? { policy_note: draft.policyNote.trim() } : {}),
    };
    try {
      const saved = await recordSourceReview(context.reportId, context.version, body);
      setLoaded({ key, rows: [...history, saved] });
      setDraft(EMPTY_DRAFT);
      setAnnouncement(`Review recorded as revision ${String(saved.number)}.`);
    } catch (caught) {
      setError({
        message: describeError(caught),
        stale: isApiError(caught) && caught.status === 409,
      });
    } finally {
      setBusy(false);
    }
  };

  const judgement = context.judgements.find((row) => row.id === judgementId);
  const full = history !== null && history.length >= MAX_REVIEW_REVISIONS;
  return (
    <section
      aria-label={`Human source reviews for ${item.label}`}
      className="min-w-0 space-y-3 text-xs text-muted"
    >
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
        Human source reviews
      </h3>
      <p>
        Human reviews are separate from the automatic grade above and never change this saved
        version. Use a reviewed snapshot to view or export the report with them.
      </p>
      {citing.length === 0 ? (
        <p>This source is not cited by a saved key judgement, so it cannot be reviewed here.</p>
      ) : (
        <>
          <div className="grid gap-2 sm:grid-cols-3">
            <label className="block" htmlFor={`${id}-judgement`}>
              Judgement
              <select
                id={`${id}-judgement`}
                className="mt-1 w-full rounded border border-line bg-surface p-2 text-text"
                value={judgementId}
                onChange={(event) => setJudgementId(event.target.value)}
              >
                {citing.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.id}
                  </option>
                ))}
              </select>
            </label>
            <label className="block" htmlFor={`${id}-kind`}>
              Review kind
              <select
                id={`${id}-kind`}
                className="mt-1 w-full rounded border border-line bg-surface p-2 text-text"
                value={kind}
                onChange={(event) => setKind(event.target.value as SourceReviewKind)}
              >
                {KINDS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block" htmlFor={`${id}-subject`}>
              Subject area (required)
              <input
                id={`${id}-subject`}
                className="mt-1 w-full rounded border border-line bg-surface p-2 text-text"
                maxLength={200}
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
              />
            </label>
          </div>
          {judgement && <p className="text-text">{judgement.statement}</p>}
          <p>{scopeText(kind, item, judgementId, context.scopeLabel)}</p>
          <Button
            variant="secondary"
            busy={loading}
            disabled={!target.subject}
            onClick={() => void load()}
          >
            Load review history
          </Button>
          {loading && <LoadingNote label="Loading review history" />}
          {loadError && <Alert tone="error">{loadError}</Alert>}
          {history === null ? (
            !loading && !loadError && <p>Load the history for this target before recording.</p>
          ) : (
            <>
              <History rows={history} reviewer={context.reviewer} />
              <p role="status" className="text-text">
                {announcement}
              </p>
              {full ? (
                <Alert tone="warning">
                  This history has reached its {MAX_REVIEW_REVISIONS}-revision limit. No further
                  corrections can be recorded. All {MAX_REVIEW_REVISIONS} retained revisions are
                  shown; none are discarded.
                </Alert>
              ) : context.canWrite ? (
                <SourceReviewForm
                  kind={kind}
                  draft={draft}
                  onChange={setDraft}
                  correcting={history.length > 0}
                  busy={busy}
                  error={error}
                  onSubmit={() => void submit()}
                  onReload={() => void load()}
                />
              ) : (
                <p>
                  You can read these reviews but cannot record source reviews on this report.
                  Recording needs write access to the report in an active team; corrections to
                  another reviewer&apos;s history need that reviewer or a team manager.
                </p>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}
