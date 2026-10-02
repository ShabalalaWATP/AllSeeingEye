import { useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import { bands, confidenceLevels } from '@/lib/api/forecastSchemas';
import { describeError } from '@/lib/api/errors';
import type { ForecastCreate } from '@/lib/api/forecasts';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

export function ForecastForm({
  anchor,
  initial,
  onSave,
  onCancel,
}: {
  anchor: Pick<ForecastCreate, 'claim_id' | 'claim_revision_id' | 'supporting' | 'contrary'>;
  initial?: ForecastCreate;
  onSave: (value: ForecastCreate, reason: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [criterion, setCriterion] = useState(initial?.criterion.description ?? '');
  const [horizon, setHorizon] = useState('');
  const [review, setReview] = useState('');
  const [band, setBand] = useState<ForecastCreate['likelihood']>(
    initial?.likelihood ?? 'realistic_possibility',
  );
  const [confidence, setConfidence] = useState<ForecastCreate['confidence']>(
    initial?.confidence ?? {
      source_quality: 'moderate',
      corroboration: 'low',
      coverage: 'low',
      limitation: '',
    },
  );
  const [reason, setReason] = useState('');
  const save = useAsyncAction(async () =>
    onSave(
      {
        ...anchor,
        criterion: { ...initial?.criterion, description: criterion },
        horizon_end: new Date(horizon).toISOString(),
        review_at: new Date(review).toISOString(),
        likelihood: band,
        confidence,
      },
      reason,
    ),
  );
  return (
    <form
      className="space-y-3 rounded border border-line p-4"
      onSubmit={(e) => {
        e.preventDefault();
        void save.run();
      }}
    >
      <TextAreaField
        label="Resolution criterion"
        value={criterion}
        maxLength={1000}
        required
        onChange={(e) => setCriterion(e.target.value)}
      />
      {initial?.criterion.metric_id && (
        <p className="text-sm text-muted">
          This replacement retains the existing quantitative criterion:{' '}
          {initial.criterion.metric_id}, {initial.criterion.direction?.replaceAll('_', ' ')}{' '}
          {initial.criterion.threshold} {initial.criterion.unit}.
        </p>
      )}
      <TextField
        label="Review date and time"
        type="datetime-local"
        required
        value={review}
        onChange={(e) => setReview(e.target.value)}
      />
      <TextField
        label="Forecast horizon date and time"
        type="datetime-local"
        required
        value={horizon}
        onChange={(e) => setHorizon(e.target.value)}
      />
      <p className="text-xs text-muted">
        Times use your device timezone. Review reminders are separate from the outcome horizon.
      </p>
      <SelectField
        options={bands.map((value) => ({ value, label: value.replaceAll('_', ' ') }))}
        label="Original PHIA likelihood band"
        value={band}
        onChange={(e) => setBand(e.target.value as typeof band)}
      />
      {(['source_quality', 'corroboration', 'coverage'] as const).map((key) => (
        <SelectField
          options={confidenceLevels.map((value) => ({ value, label: value }))}
          key={key}
          label={`Forecast confidence: ${key.replaceAll('_', ' ')}`}
          value={confidence[key]}
          onChange={(e) =>
            setConfidence({
              ...confidence,
              [key]: e.target.value as typeof confidence.source_quality,
            })
          }
        />
      ))}
      <TextAreaField
        label="Confidence limitation"
        required
        maxLength={1000}
        value={confidence.limitation}
        onChange={(e) => setConfidence({ ...confidence, limitation: e.target.value })}
      />
      {initial && (
        <TextAreaField
          label="Supersession reason"
          required
          maxLength={2000}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
      )}
      <p className="text-xs">
        The selected reviewed revision's supporting and contrary passages are retained with this
        forecast. The report stays frozen.
      </p>
      {save.error && <Alert tone="error">{describeError(save.error)}</Alert>}
      {anchor.supporting.length === 0 && (
        <Alert tone="warning">
          This reviewed claim has no supporting passage. Choose a reviewed revision with supporting
          evidence.
        </Alert>
      )}
      <Button type="submit" busy={save.busy} disabled={anchor.supporting.length === 0}>
        {initial ? 'Save replacement forecast' : 'Save forecast'}
      </Button>{' '}
      <Button variant="secondary" disabled={save.busy} onClick={onCancel}>
        Cancel forecast
      </Button>
    </form>
  );
}
