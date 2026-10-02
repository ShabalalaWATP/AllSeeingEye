import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { currentForecast } from '@/lib/api/forecastSchemas';
import type { Forecast } from '@/lib/api/forecastSchemas';
import { supersedeForecast } from '@/lib/api/forecasts';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { ForecastForm } from './ForecastForm';
import { ForecastReview } from './ForecastReview';

export function ForecastCard({
  value,
  version,
  canEdit,
  onSaved,
}: {
  value: Forecast;
  version: number;
  canEdit: boolean;
  onSaved: () => void;
}) {
  const [now] = useState(() => Date.now());
  const [mode, setMode] = useState<'review' | 'replace' | null>(null);
  const current = currentForecast(value);
  const latest = value.history.decisions
    .filter((row) => row.forecast_version_id === current.version_id)
    .at(-1);
  const state = latest?.state ?? (Date.parse(current.horizon_end) <= now ? 'due' : 'open');
  const request = useScopedRequest();
  const initial = {
    claim_id: current.claim_id,
    claim_revision_id: current.claim_version_id,
    supporting: current.supporting.map((row) => ({
      evidence_label: row.evidence_id,
      excerpt_sha256: row.passage_id,
    })),
    contrary: current.contrary.map((row) => ({
      evidence_label: row.evidence_id,
      excerpt_sha256: row.passage_id,
    })),
    horizon_end: current.horizon_end,
    review_at: current.review_at,
    criterion: current.criterion,
    likelihood: current.likelihood,
    confidence: current.confidence,
  };
  return (
    <div className="space-y-3">
      <h3 className="font-medium">{current.criterion.description}</h3>
      <p>
        Version {current.version}: {current.likelihood.replaceAll('_', ' ')} · Outcome state:{' '}
        {state}
        {latest?.outcome != null ? ` (${String(latest.outcome)})` : ''}
      </p>
      <p className="text-sm">
        Review: {new Date(current.review_at).toLocaleString()} · Horizon:{' '}
        {new Date(current.horizon_end).toLocaleString()}
      </p>
      {Date.parse(current.review_at) <= now && ['open', 'due'].includes(state) && (
        <p className="text-ember">Review due</p>
      )}
      <details>
        <summary className="cursor-pointer">Immutable forecast history</summary>
        {value.history.versions.map((row) => (
          <div key={row.version_id} className="my-3 border-l border-line pl-3 text-sm">
            <p>
              Version {row.version}, issued {new Date(row.issued_at).toLocaleString()}:{' '}
              {row.likelihood.replaceAll('_', ' ')}
            </p>
            <p>{row.criterion.description}</p>
            <p>
              Confidence: source quality {row.confidence.source_quality}, corroboration{' '}
              {row.confidence.corroboration}, coverage {row.confidence.coverage}.{' '}
              {row.confidence.limitation}
            </p>
            <p>
              Supporting passages: {row.supporting.map((ref) => ref.evidence_id).join(', ')}.
              Contrary passages: {row.contrary.map((ref) => ref.evidence_id).join(', ') || 'none'}.
            </p>
            {value.history.decisions
              .filter((decision) => decision.forecast_version_id === row.version_id)
              .map((decision) => (
                <div key={decision.id} className="mt-2">
                  <p>
                    {decision.state}
                    {decision.outcome != null ? ` ${String(decision.outcome)}` : ''},{' '}
                    {new Date(decision.recorded_at).toLocaleString()}: {decision.reason}
                  </p>
                  <p>
                    Reviewer {decision.actor_id}
                    {decision.corrects_decision_id ? ' · correction of prior decision' : ''}
                  </p>
                  <p>
                    Outcome evidence:{' '}
                    {decision.evidence
                      .map((ref) => `${ref.evidence_id} in frozen version ${ref.report_version_id}`)
                      .join('; ') || 'none'}
                  </p>
                </div>
              ))}
          </div>
        ))}
      </details>
      {canEdit && mode === null && (
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setMode('review')}>
            Review forecast
          </Button>
          {['open', 'due'].includes(state) && (
            <Button variant="secondary" onClick={() => setMode('replace')}>
              Supersede forecast
            </Button>
          )}
        </div>
      )}
      {mode === 'review' && (
        <ForecastReview
          value={value}
          version={version}
          onCancel={() => setMode(null)}
          onSaved={() => {
            setMode(null);
            onSaved();
          }}
        />
      )}
      {mode === 'replace' && (
        <ForecastForm
          anchor={initial}
          initial={initial}
          onCancel={() => setMode(null)}
          onSave={async (replacement, reason) => {
            const signal = request();
            await supersedeForecast(
              value.anchor.report_id,
              version,
              value.anchor.id,
              {
                expected_version_id: current.version_id,
                previous_decision_id: latest?.id ?? null,
                reason,
                replacement,
              },
              signal,
            );
            signal.throwIfAborted();
            setMode(null);
            onSaved();
          }}
        />
      )}
    </div>
  );
}
