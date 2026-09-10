import type { RfPropagation } from '@/lib/map/rfDraft';
import { useId } from 'react';

export function RfAnalysisAction({
  mode,
  frequencyMHz,
  validEnvironment,
  ready,
  readiness,
  busy,
  error,
  onAnalyse,
  progress,
  automation,
}: {
  mode: RfPropagation;
  frequencyMHz: number;
  validEnvironment: boolean;
  ready: boolean;
  readiness: string;
  busy: boolean;
  error: string | null;
  onAnalyse: () => void;
  progress?: string | null;
  automation: { enabled: boolean; armed: boolean; setEnabled: (value: boolean) => void };
}) {
  const autoId = useId();
  return (
    <div className="rf-analysis-action">
      {mode === 'terrain' && frequencyMHz < 30 && (
        <p role="alert" className="rf-notice-warning">
          Terrain analysis requires at least 30 MHz. Choose an HF model below this frequency.
        </p>
      )}
      {mode.startsWith('hf-') && frequencyMHz > 30 && (
        <p role="alert" className="rf-notice-warning">
          HF scenarios require 1.6 to 30 MHz.
        </p>
      )}
      {!validEnvironment && (
        <p role="alert" className="rf-notice-warning">
          Complete every model setting with a valid number.
        </p>
      )}
      <p className="rf-readiness">
        <span className="rf-readiness-dot" data-ready={ready} aria-hidden="true" />
        {busy
          ? (progress ?? 'Calculating this study. Changing inputs cancels the request.')
          : readiness}
      </p>
      <div>
        <label className="rf-auto-toggle" htmlFor={autoId}>
          <input
            id={autoId}
            type="checkbox"
            className="rf-checkbox"
            checked={automation.enabled}
            onChange={(event) => automation.setEnabled(event.target.checked)}
          />
          Auto update after changes
        </label>
        <p className="rf-help">
          {!automation.armed
            ? 'Starts after your first analysis.'
            : automation.enabled
              ? 'Updates after edits, at most twice a minute.'
              : 'Paused. Analyse manually or enable updates.'}
        </p>
      </div>
      <button
        type="button"
        disabled={busy || !ready}
        onClick={onAnalyse}
        className="rf-primary-button"
      >
        {busy
          ? 'Analysing...'
          : mode === 'terrain'
            ? 'Analyse terrain'
            : mode === 'hf-groundwave'
              ? 'Analyse HF groundwave'
              : 'Calculate skywave scenario'}
      </button>
      {error && (
        <p role="alert" className="rf-notice-warning">
          {error}
        </p>
      )}
    </div>
  );
}
