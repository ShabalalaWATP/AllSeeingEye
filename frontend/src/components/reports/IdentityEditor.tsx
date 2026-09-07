import { useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField } from '@/components/ui/Field';
import { createIdentity, updateIdentity } from '@/lib/api/identities';
import type { IdentityCreate, IdentityRevision } from '@/lib/api/identities';
import type { EvidenceItem } from '@/lib/api/reports';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { ClaimCitationPicker } from './ClaimCitationPicker';

export function IdentityEditor({
  reportId,
  version,
  label,
  subject,
  evidence,
  current,
  onSaved,
  onCancel,
}: {
  reportId: string;
  version: number;
  label: string;
  subject: string;
  evidence: EvidenceItem[];
  current?: IdentityRevision;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [disposition, setDisposition] = useState<IdentityRevision['disposition']>(
    current?.disposition ?? 'unresolved',
  );
  const [rationale, setRationale] = useState('');
  const [conflicts, setConflicts] = useState(current?.unresolved_conflicts ?? []);
  const [citations, setCitations] = useState<NonNullable<IdentityCreate['citations']>>(
    current?.citations.map((row) => ({
      label: row.label,
      relation: row.relation,
      field: row.excerpt.field,
      start: row.excerpt.start,
      end: row.excerpt.end,
      text: row.excerpt.text,
    })) ?? [],
  );
  const request = useScopedRequest();
  const save = useAsyncAction(async () => {
    const signal = request();
    const body = {
      candidate_label: label,
      disposition,
      rationale,
      unresolved_conflicts: conflicts,
      citations,
    };
    if (current)
      await updateIdentity(current.decision_id, { ...body, base_revision_id: current.id }, signal);
    else await createIdentity({ ...body, report_id: reportId, version_number: version }, signal);
    signal.throwIfAborted();
    onSaved();
  });
  return (
    <form
      aria-label={current ? 'Correct identity review' : 'Review identity'}
      className="space-y-4 rounded border border-line p-4"
      onSubmit={(event) => {
        event.preventDefault();
        void save.run();
      }}
    >
      <fieldset disabled={save.busy} className="space-y-4">
        <p className="text-sm">
          Does candidate {label} identify <strong>{subject}</strong>?
        </p>
        <p className="text-xs text-muted">
          This is your attributed judgement. It does not merge identities or establish ownership.
        </p>
        <SelectField
          label="Identity decision"
          value={disposition}
          onChange={(event) =>
            setDisposition(event.target.value as IdentityRevision['disposition'])
          }
          options={[
            { value: 'unresolved', label: 'Unresolved' },
            { value: 'matched', label: 'Matched' },
            { value: 'rejected', label: 'Rejected' },
            ...(current ? [{ value: 'withdrawn', label: 'Withdrawn' }] : []),
          ]}
        />
        <TextAreaField
          label="Decision rationale"
          required
          maxLength={1200}
          value={rationale}
          onChange={(event) => setRationale(event.target.value)}
        />
        {conflicts.map((conflict, index) => (
          <div key={index} className="space-y-2">
            <TextAreaField
              label={`Unresolved conflict ${index + 1}`}
              required
              maxLength={1200}
              value={conflict}
              onChange={(event) =>
                setConflicts(conflicts.map((item, i) => (i === index ? event.target.value : item)))
              }
            />
            <Button
              type="button"
              variant="secondary"
              onClick={() => setConflicts(conflicts.filter((_, i) => i !== index))}
            >
              Remove conflict {index + 1}
            </Button>
          </div>
        ))}
        {conflicts.length < 20 && (
          <Button
            type="button"
            variant="secondary"
            onClick={() => setConflicts([...conflicts, ''])}
          >
            Add unresolved conflict
          </Button>
        )}
        {citations.map((row, index) => (
          <div key={index} className="border-l border-line pl-3 text-sm">
            <p>
              {row.label} · {row.relation}: {row.text}
            </p>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setCitations(citations.filter((_, i) => i !== index))}
            >
              Remove excerpt {index + 1}
            </Button>
          </div>
        ))}
        {citations.length < 20 && (
          <ClaimCitationPicker
            evidence={evidence}
            onAdd={(row) =>
              setCitations((previous) =>
                previous.some((item) => JSON.stringify(item) === JSON.stringify(row))
                  ? previous
                  : [...previous, row],
              )
            }
          />
        )}
        {save.error && (
          <Alert tone="error">
            {describeError(save.error)} Your draft remains here. Cancel to reload the latest review
            before trying again.
          </Alert>
        )}
        <div className="flex gap-2">
          <Button type="submit" disabled={!rationale.trim()}>
            {save.busy ? 'Saving review…' : 'Save identity review'}
          </Button>
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel review
          </Button>
        </div>
      </fieldset>
    </form>
  );
}
