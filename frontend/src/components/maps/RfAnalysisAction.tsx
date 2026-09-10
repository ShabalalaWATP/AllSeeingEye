import type { RfPropagation } from '@/lib/map/rfDraft';

export function RfAnalysisAction({
  mode,
  frequencyMHz,
  validEnvironment,
  ready,
  readiness,
  busy,
  error,
  onAnalyse,
}: {
  mode: RfPropagation;
  frequencyMHz: number;
  validEnvironment: boolean;
  ready: boolean;
  readiness: string;
  busy: boolean;
  error: string | null;
  onAnalyse: () => void;
}) {
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
        {busy ? 'Calculating this study. Changing inputs cancels the request.' : readiness}
      </p>
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
