import { useId, useState } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import {
  VERDICT_LABELS as VERDICT_LABEL,
  VERDICT_VALUES,
  type CitationVerdict,
  type CitationVerdictInput,
  type CitationVerdictList,
  type CitationVerdictValue,
} from '@/lib/api/citationVerdicts';
import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';

export interface CitationAnchorProps {
  judgementId: string;
  label: string;
  relation: 'supporting' | 'contradicting';
}

/** Each reviewer's latest verdict on one citation; earlier ones are kept but superseded. */
function latestIds(rows: readonly CitationVerdict[]): Set<string> {
  const latest = new Map<string, CitationVerdict>();
  for (const row of rows) latest.set(row.reviewer_id, row);
  return new Set(Array.from(latest.values(), (row) => row.id));
}

function VerdictHistory({
  rows,
  reviewer,
}: {
  rows: readonly CitationVerdict[];
  reviewer: (id: string) => string;
}) {
  if (rows.length === 0) return <p>No verdicts recorded for this citation.</p>;
  const current = latestIds(rows);
  return (
    <ul className="space-y-2" aria-label="Recorded verdicts">
      {rows.map((row) => (
        <li key={row.id} className="border-l-2 border-line pl-2">
          <p className="text-text">
            {reviewer(row.reviewer_id)} · {VERDICT_LABEL[row.verdict]} ·{' '}
            {formatUtc(row.recorded_at)}
            {current.has(row.id) ? '' : ' · Superseded by a later verdict from this reviewer'}
          </p>
          {row.note && <p className="whitespace-pre-wrap">{row.note}</p>}
        </li>
      ))}
    </ul>
  );
}

export function CitationVerdictControls({
  anchor,
  list,
  reviewer,
  onRecord,
}: {
  anchor: CitationAnchorProps;
  list: CitationVerdictList;
  reviewer: (id: string) => string;
  onRecord: (body: CitationVerdictInput) => Promise<CitationVerdict>;
}) {
  const id = useId();
  const [choice, setChoice] = useState<CitationVerdictValue | null>(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState('');
  const rows = list.verdicts.filter(
    (row) =>
      row.judgement_id === anchor.judgementId &&
      row.label === anchor.label &&
      row.relation === anchor.relation,
  );
  const submit = async () => {
    if (!choice || busy) return;
    setBusy(true);
    setError(null);
    setAnnouncement('');
    try {
      const trimmed = note.trim();
      const saved = await onRecord({
        judgement_id: anchor.judgementId,
        label: anchor.label,
        relation: anchor.relation,
        verdict: choice,
        note: trimmed ? trimmed : null,
      });
      setChoice(null);
      setNote('');
      setAnnouncement(`Verdict recorded: ${VERDICT_LABEL[saved.verdict]}.`);
    } catch (caught) {
      // The draft stays so the reviewer can retry or copy it.
      setError(describeError(caught));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="space-y-2 border-t border-line pt-2">
      <p className="font-medium text-text">Human verdicts</p>
      <VerdictHistory rows={rows} reviewer={reviewer} />
      <p role="status" className="text-text">
        {announcement}
      </p>
      {list.can_record ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <div
            role="radiogroup"
            aria-label={`Your verdict on ${anchor.label} as ${anchor.relation} evidence for ${anchor.judgementId}`}
            className="flex flex-wrap gap-2"
          >
            {VERDICT_VALUES.map((value) => (
              <label
                key={value}
                className="inline-flex items-center gap-1 rounded border border-line px-2 py-1 text-text has-[:checked]:border-ember"
              >
                <input
                  type="radio"
                  name={`${id}-verdict`}
                  value={value}
                  checked={choice === value}
                  onChange={() => setChoice(value)}
                />
                {VERDICT_LABEL[value]}
              </label>
            ))}
          </div>
          <label className="block" htmlFor={`${id}-note`}>
            Note (optional, up to {list.note_limit} characters)
          </label>
          <textarea
            id={`${id}-note`}
            className="w-full rounded border border-line bg-surface p-2 text-text"
            maxLength={list.note_limit}
            rows={2}
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
          {error && <Alert tone="error">{error}</Alert>}
          <Button type="submit" variant="secondary" busy={busy} disabled={!choice}>
            Record verdict
          </Button>
        </form>
      ) : (
        <p>
          You can read these verdicts but cannot record verdicts on this report. Archived teams are
          read-only, and recording needs write access to the report&apos;s personal or team scope.
        </p>
      )}
    </div>
  );
}
