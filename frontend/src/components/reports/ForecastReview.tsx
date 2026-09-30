import { useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import type { ClaimRevision } from '@/lib/api/claims';
import { currentForecast } from '@/lib/api/forecastSchemas';
import type { Forecast } from '@/lib/api/forecastSchemas';
import { reviewForecast } from '@/lib/api/forecasts';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { ForecastClaimPicker } from './ForecastClaimPicker';

export function ForecastReview({
  value,
  version,
  onSaved,
  onCancel,
}: {
  value: Forecast;
  version: number;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const current = currentForecast(value);
  const latest = value.history.decisions
    .filter((row) => row.forecast_version_id === current.version_id)
    .at(-1);
  const [outcome, setOutcome] = useState('unresolved');
  const [reason, setReason] = useState('');
  const [link, setLink] = useState('');
  const [edition, setEdition] = useState(1);
  const [source, setSource] = useState<{ id: string; version: number } | null>(null);
  const [claim, setClaim] = useState<ClaimRevision | null>(null);
  const [citation, setCitation] = useState('');
  const request = useScopedRequest();
  const chosen = claim?.citations.find((row) => `${row.label}:${row.excerpt.sha256}` === citation);
  const save = useAsyncAction(async () => {
    const signal = request();
    await reviewForecast(
      value.anchor.report_id,
      version,
      value.anchor.id,
      {
        expected_version_id: current.version_id,
        state: outcome === 'unresolved' ? 'unresolved' : 'resolved',
        outcome: outcome === 'unresolved' ? null : outcome === 'true',
        reason,
        previous_decision_id: latest?.id ?? null,
        corrects_decision_id:
          latest && ['resolved', 'unresolved'].includes(latest.state) ? latest.id : null,
        evidence: [],
        outcome_evidence:
          source && claim && chosen && outcome !== 'unresolved'
            ? [
                {
                  report_id: source.id,
                  version: source.version,
                  claim_id: claim.claim_id,
                  claim_revision_id: claim.id,
                  citation: { evidence_label: chosen.label, excerpt_sha256: chosen.excerpt.sha256 },
                },
              ]
            : [],
      },
      signal,
    );
    signal.throwIfAborted();
    onSaved();
  });
  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        void save.run();
      }}
    >
      <SelectField
        options={[
          { value: 'unresolved', label: 'Unresolved, horizon passed but outcome not established' },
          { value: 'true', label: 'Resolved true, later observation supports criterion' },
          { value: 'false', label: 'Resolved false, later observation disproves criterion' },
        ]}
        label="Review decision"
        value={outcome}
        onChange={(e) => setOutcome(e.target.value)}
      />
      <TextAreaField
        label="Review reason"
        required
        maxLength={2000}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      {outcome !== 'unresolved' && (
        <>
          <p>
            Choose a later independently frozen report in the same workspace and an exact reviewed
            outcome passage.
          </p>
          <TextField
            label="Later report link"
            value={link}
            onChange={(e) => {
              setLink(e.target.value);
              setSource(null);
              setClaim(null);
            }}
          />
          <TextField
            label="Later report version"
            type="number"
            min={1}
            value={edition}
            onChange={(e) => {
              setEdition(Number(e.target.value));
              setSource(null);
              setClaim(null);
            }}
          />
          <Button
            variant="secondary"
            disabled={!/\/reports\/([0-9a-f-]{36})(?:[/?#]|$)/i.test(link)}
            onClick={() => {
              const match = /\/reports\/([0-9a-f-]{36})(?:[/?#]|$)/i.exec(link);
              if (match?.[1]) {
                setSource({ id: match[1], version: edition });
                setClaim(null);
              }
            }}
          >
            Load later reviewed claims
          </Button>
          {source && (
            <ForecastClaimPicker
              key={`${source.id}:${source.version}`}
              reportId={source.id}
              version={source.version}
              onChoose={(row) => {
                setClaim(row);
                setCitation('');
              }}
            />
          )}
          {claim && (
            <SelectField
              options={[
                { value: '', label: 'Choose a frozen passage' },
                ...claim.citations.map((row) => ({
                  value: `${row.label}:${row.excerpt.sha256}`,
                  label: `${row.label}: ${row.excerpt.text}`,
                })),
              ]}
              label="Outcome evidence passage"
              required
              value={citation}
              onChange={(e) => setCitation(e.target.value)}
            />
          )}
        </>
      )}
      {latest && <p>This appends a correction. The previous review stays in the history.</p>}
      {save.error && <Alert tone="error">{describeError(save.error)}</Alert>}
      <Button type="submit" busy={save.busy} disabled={outcome !== 'unresolved' && !chosen}>
        Record review
      </Button>{' '}
      <Button variant="secondary" onClick={onCancel}>
        Cancel review
      </Button>
    </form>
  );
}
