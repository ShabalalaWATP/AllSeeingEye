import { useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField } from '@/components/ui/Field';
import { createClaim, updateClaim } from '@/lib/api/claims';
import type { ClaimCreate, ClaimRevision } from '@/lib/api/claims';
import type { EvidenceItem } from '@/lib/api/reports';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { ClaimCitationPicker } from './ClaimCitationPicker';

export function ClaimEditor({
  reportId,
  version,
  evidence,
  current,
  onSaved,
  onCancel,
}: {
  reportId: string;
  version: number;
  evidence: EvidenceItem[];
  current?: ClaimRevision;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [statement, setStatement] = useState(current?.statement ?? '');
  const [kind, setKind] = useState<ClaimCreate['kind']>(current?.kind ?? 'reported_fact');
  const [state, setState] = useState<ClaimRevision['state']>(current?.state ?? 'proposed');
  const [reason, setReason] = useState('');
  const [conflicts, setConflicts] = useState(current?.unresolved_conflicts.join('\n') ?? '');
  const [citations, setCitations] = useState<ClaimCreate['citations']>(
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
      statement,
      kind,
      state,
      reason,
      citations,
      unresolved_conflicts: conflicts.split('\n').filter((text) => text.trim()),
    };
    if (current)
      await updateClaim(current.claim_id, { ...body, base_revision_id: current.id }, signal);
    else await createClaim({ ...body, report_id: reportId, version_number: version }, signal);
    signal.throwIfAborted();
    onSaved();
  });
  return (
    <form
      aria-label={current ? 'Revise claim' : 'Add claim'}
      className="space-y-4 rounded border border-line p-4"
      onSubmit={(event) => {
        event.preventDefault();
        void save.run();
      }}
    >
      <fieldset disabled={save.busy} className="space-y-4">
        <p className="text-sm text-muted">
          Write one attributed assertion. Exact excerpts preserve what was captured; they do not
          prove the assertion.
        </p>
        <TextAreaField
          label="Claim statement"
          required
          maxLength={1200}
          value={statement}
          onChange={(event) => setStatement(event.target.value)}
        />
        <SelectField
          options={[
            { value: 'reported_fact', label: 'Attributed reporting' },
            { value: 'analytical_inference', label: 'Analytical inference' },
          ]}
          label="Claim type"
          value={kind}
          onChange={(event) => setKind(event.target.value as ClaimCreate['kind'])}
        ></SelectField>
        {current && (
          <SelectField
            options={[
              { value: 'proposed', label: 'Proposed' },
              { value: 'reviewed', label: 'Reviewed' },
              { value: 'withdrawn', label: 'Withdrawn' },
            ]}
            label="Review state"
            value={state}
            onChange={(event) => setState(event.target.value as ClaimRevision['state'])}
          ></SelectField>
        )}
        {citations.map((row, index) => (
          <div key={index} className="border-l-2 border-line pl-3 text-sm">
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
        <TextAreaField
          label="Unresolved conflicts"
          hint="One conflict per line, up to 20. Leave blank if none are recorded."
          value={conflicts}
          onChange={(event) => setConflicts(event.target.value)}
        />
        <TextAreaField
          label="Reason for this revision"
          required
          maxLength={1200}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
        {save.error && (
          <Alert tone="error">
            {describeError(save.error)}
            {save.error.status === 409 &&
              ' Close the editor and reload the latest claim before revising again.'}
          </Alert>
        )}
        <div className="flex gap-2">
          <Button
            type="submit"
            disabled={save.busy || !statement.trim() || !reason.trim() || citations.length === 0}
          >
            {save.busy ? 'Saving…' : current ? 'Save new revision' : 'Save proposed claim'}
          </Button>
          <Button type="button" variant="secondary" disabled={save.busy} onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </fieldset>
    </form>
  );
}
