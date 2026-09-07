import { useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField } from '@/components/ui/Field';
import { createRelationship, updateRelationship } from '@/lib/api/relationships';
import type { RelationshipCreate, RelationshipRevision } from '@/lib/api/relationships';
import type { EvidenceItem } from '@/lib/api/reports';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { ClaimCitationPicker } from './ClaimCitationPicker';

export function RelationshipEditor({
  reportId,
  version,
  label,
  evidence,
  current,
  onSaved,
  onCancel,
  onReload,
}: {
  reportId: string;
  version: number;
  label: string;
  evidence: EvidenceItem[];
  current?: RelationshipRevision;
  onSaved: () => void;
  onCancel: () => void;
  onReload?: () => void;
}) {
  const [disposition, setDisposition] = useState<RelationshipRevision['disposition']>(
    current?.disposition ?? 'unresolved',
  );
  const [rationale, setRationale] = useState('');
  const [conflicts, setConflicts] = useState(current?.unresolved_conflicts ?? []);
  const [citations, setCitations] = useState<NonNullable<RelationshipCreate['citations']>>(
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
      evidence_label: label,
      disposition,
      rationale,
      unresolved_conflicts: conflicts,
      citations,
    };
    if (current)
      await updateRelationship(
        current.relationship_id,
        { ...body, base_revision_id: current.id },
        signal,
      );
    else
      await createRelationship({ ...body, report_id: reportId, version_number: version }, signal);
    signal.throwIfAborted();
    onSaved();
  });
  return (
    <form
      aria-label={current ? 'Correct relationship review' : 'Review relationship'}
      className="space-y-4 rounded border border-line p-4"
      onSubmit={(event) => {
        event.preventDefault();
        void save.run();
      }}
    >
      <fieldset disabled={save.busy} className="space-y-4">
        <p className="text-sm">Review the source-reported relationship in evidence {label}.</p>
        <p className="text-xs text-muted">
          This is your attributed judgement. It does not establish ownership, identity or current
          validity.
        </p>
        <SelectField
          label="Relationship assessment"
          value={disposition}
          onChange={(event) =>
            setDisposition(event.target.value as RelationshipRevision['disposition'])
          }
          options={[
            { value: 'unresolved', label: 'Unresolved' },
            { value: 'supported', label: 'Supported' },
            { value: 'disputed', label: 'Disputed' },
            ...(current ? [{ value: 'withdrawn', label: 'Withdrawn' }] : []),
          ]}
        />
        <TextAreaField
          label="Assessment rationale"
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
              {row.label} / {row.relation}: {row.text}
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
            {describeError(save.error)} Your draft remains here. Reloading discards this draft and
            fetches the current revision.
            {onReload && (
              <Button type="button" variant="secondary" onClick={onReload}>
                Discard draft and reload review
              </Button>
            )}
          </Alert>
        )}
        <div className="flex gap-2">
          <Button type="submit" disabled={!rationale.trim()}>
            {save.busy ? 'Saving review...' : 'Save relationship review'}
          </Button>
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel review
          </Button>
        </div>
      </fieldset>
    </form>
  );
}
