import { useState } from 'react';
import { calculateRf, RF_FIELDS } from '@/lib/map/rfPlanning';
import type { RfInputs } from '@/lib/map/rfPlanning';
import { RF_PRESETS } from '@/lib/map/rfPresets';
import { rfMapEstimate } from '@/lib/map/rfMap';
import type { RfMapEstimate } from '@/lib/map/rfMap';
import type { Position } from '@/lib/map/geoJsonTypes';
import { measure } from '@/lib/map/measurements';
import { RfResults } from './RfResults';
import { RfPowerInput } from './RfPowerInput';
import { RfPositions } from './RfPositions';
import { RfModelControls, rfEnvironmentValid } from './RfModelControls';
import { RfReferences } from './RfReferences';
import { RfPresetSelect } from './RfPresetSelect';
import { useRfAnalysis } from './useRfAnalysis';
import { RfAnalysisResults } from './RfAnalysisResults';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { createRfDraft, RF_ENVIRONMENT_DEFAULTS } from '@/lib/map/rfDraft';
import type { RfDraft } from '@/lib/map/rfDraft';

const BASIC_FIELDS = new Set<keyof RfInputs>([
  'frequencyMHz',
  'transmitHeightM',
  'receiveHeightM',
  'distanceKm',
]);
export interface RfCalculatorPanelProps {
  measuredDistanceKm?: number | undefined;
  origin?: Position | null;
  receiver?: Position | null;
  picking?: 'origin' | 'receiver' | null;
  onPick?: ((point: 'origin' | 'receiver' | null) => void) | undefined;
  onOverlayChange?: (estimate: RfMapEstimate | null) => void;
  overlayVisible?: boolean;
  draft?: RfDraft;
  onDraftChange?: (draft: RfDraft) => void;
  onClearReceiver?: (() => void) | undefined;
  analysis?: RfAnalysis | null;
  onAnalysisChange?: ((value: RfAnalysis | null) => void) | undefined;
}

export function RfCalculatorPanel({
  measuredDistanceKm,
  origin = null,
  receiver = null,
  picking = null,
  onPick,
  onOverlayChange,
  overlayVisible = false,
  draft,
  onDraftChange,
  onClearReceiver,
  analysis,
  onAnalysisChange,
}: RfCalculatorPanelProps) {
  const [localDraft, setLocalDraft] = useState(() => createRfDraft());
  const currentDraft = draft ?? localDraft;
  const { values, presetId } = currentDraft;
  const mode = currentDraft.propagation ?? 'terrain';
  const [localAnalysis, setLocalAnalysis] = useState<RfAnalysis | null>(null);
  const changeAnalysis = onAnalysisChange ?? setLocalAnalysis;
  const currentAnalysis = analysis === undefined ? localAnalysis : analysis;
  const setDraft = onDraftChange ?? setLocalDraft;
  const preset = RF_PRESETS.find((item) => item.id === presetId) ?? RF_PRESETS[0];
  const input = Object.fromEntries(
    Object.entries(values).map(([key, value]) => [key, value.trim() ? Number(value) : NaN]),
  ) as unknown as RfInputs;
  if (origin && receiver) input.distanceKm = measure([origin, receiver], 'distance').metres / 1000;
  const worker = useRfAnalysis(input, currentDraft, origin, receiver, changeAnalysis);
  const update = (next: RfDraft) => {
    setDraft(next);
    onOverlayChange?.(null);
    changeAnalysis(null);
  };
  let result: ReturnType<typeof calculateRf> | null = null;
  let estimate: RfMapEstimate | null = null;
  let error: string | null = null;
  let mapError: string | null = null;
  try {
    if (mode !== 'hf-skywave')
      result = calculateRf(mode === 'free-space' ? input : { ...input, distanceKm: 1 });
    else if (
      !Number.isFinite(input.frequencyMHz) ||
      input.frequencyMHz < 1.6 ||
      input.frequencyMHz > 30
    )
      throw new Error('HF frequency: enter a value from 1.6 to 30 MHz.');
    if (origin && mode === 'free-space') {
      try {
        estimate = rfMapEstimate(input, origin, receiver);
      } catch (caught) {
        mapError = caught instanceof Error ? caught.message : 'Check the map position.';
      }
    }
  } catch (caught) {
    error = caught instanceof Error ? caught.message : 'Check the inputs.';
  }
  const change = (key: keyof RfInputs, value: string) => {
    update({ ...currentDraft, values: { ...values, [key]: value }, presetId: 'custom' });
  };
  const field = ({ key, label, min, max }: (typeof RF_FIELDS)[number]) => (
    <label key={key} className="block text-muted">
      {label}
      {key === 'transmitHeightM' || key === 'receiveHeightM' ? ' (AGL)' : ''}
      <input
        aria-label={label}
        type="number"
        min={min}
        max={max}
        step="any"
        value={
          key === 'distanceKm' && origin && receiver ? input.distanceKm.toFixed(3) : values[key]
        }
        readOnly={key === 'distanceKm' && !!origin && !!receiver}
        onChange={(event) => change(key, event.target.value)}
        className="mt-1 w-full rounded border border-line bg-ground p-2 text-text read-only:opacity-60"
      />
    </label>
  );
  return (
    <section aria-label="RF planning calculator" className="space-y-4 text-xs">
      <header>
        <h2 className="font-mono uppercase tracking-widest text-cyan">Radio link planner</h2>
        <p className="mt-2 text-muted">
          Choose a propagation model, enter the radio settings and place the transmitter. Run an
          explicit analysis when ready.
        </p>
      </header>
      <RfModelControls draft={currentDraft} onChange={update} />
      <RfPresetSelect
        presetId={presetId}
        onSelect={(selected) => {
          update({
            ...currentDraft,
            values: createRfDraft(selected.values, selected.id).values,
            presetId: selected.id,
            propagation:
              selected.id === 'custom' || mode === 'free-space'
                ? mode
                : (selected.propagation ?? (selected.values.frequencyMHz >= 30 ? 'terrain' : mode)),
            environment: {
              ...RF_ENVIRONMENT_DEFAULTS,
              ...currentDraft.environment,
              ...selected.environment,
            },
          });
        }}
      />
      <RfPositions
        origin={origin}
        receiver={receiver}
        picking={picking}
        onPick={onPick}
        onClearReceiver={onClearReceiver}
      />
      {mode === 'free-space' &&
        measuredDistanceKm !== undefined &&
        Number.isFinite(measuredDistanceKm) &&
        measuredDistanceKm > 0 &&
        !(origin && receiver) && (
          <button
            type="button"
            className="min-h-9 rounded border border-line px-2 text-cyan"
            onClick={() => change('distanceKm', measuredDistanceKm.toFixed(3))}
          >
            Use measured path ({measuredDistanceKm.toFixed(3)} km)
          </button>
        )}
      {mode !== 'hf-skywave' && (
        <RfPowerInput dbm={values.transmitDbm} onChange={(value) => change('transmitDbm', value)} />
      )}
      <p className="text-muted">
        Antenna heights are metres above local ground (AGL). Ground elevation is obtained separately
        when you analyse terrain; it is not mast height.
      </p>
      <div className="grid grid-cols-2 gap-3">
        {RF_FIELDS.filter(({ key }) =>
          mode === 'hf-skywave'
            ? key === 'frequencyMHz'
            : BASIC_FIELDS.has(key) &&
              (key !== 'distanceKm' ||
                mode === 'free-space' ||
                (mode === 'terrain' && !!origin && !!receiver)),
        ).map(field)}
      </div>
      {mode !== 'hf-skywave' && (
        <details className="rounded border border-line p-3">
          <summary className="cursor-pointer text-text">
            Advanced radio settings (dBm, gains and losses)
          </summary>
          <div className="mt-3 grid grid-cols-2 gap-3">
            {RF_FIELDS.filter(({ key }) => !BASIC_FIELDS.has(key)).map(field)}
          </div>
        </details>
      )}
      {error && (
        <p role="alert" className="text-amber-300">
          {error}
        </p>
      )}
      {mode === 'free-space' && result && <RfResults result={result} />}
      {mode !== 'free-space' && (
        <div className="space-y-3 border-t border-line pt-3">
          {!origin && <p className="text-muted">Place a transmitter before analysis.</p>}
          {mode === 'terrain' && input.frequencyMHz < 30 && (
            <p role="alert">
              Terrain analysis requires at least 30 MHz. Choose an HF model below this frequency.
            </p>
          )}
          {mode.startsWith('hf-') && input.frequencyMHz > 30 && (
            <p role="alert">HF scenarios require 1.6 to 30 MHz.</p>
          )}
          {!rfEnvironmentValid(currentDraft) && (
            <p role="alert">Complete every model setting with a valid number.</p>
          )}
          <button
            type="button"
            disabled={
              worker.busy ||
              !origin ||
              (mode === 'hf-skywave' ? !!error : !result) ||
              !rfEnvironmentValid(currentDraft) ||
              (mode === 'terrain' ? input.frequencyMHz < 30 : input.frequencyMHz > 30)
            }
            onClick={() => {
              void worker.analyse();
            }}
            className="min-h-11 w-full rounded border border-cyan/40 bg-cyan/10 px-3 text-cyan disabled:opacity-40"
          >
            {worker.busy
              ? 'Analysing...'
              : mode === 'terrain'
                ? 'Analyse terrain'
                : mode === 'hf-groundwave'
                  ? 'Analyse HF groundwave'
                  : 'Calculate skywave scenario'}
          </button>
          {worker.error && (
            <p role="alert" className="text-amber-300">
              {worker.error}
            </p>
          )}
          {currentAnalysis && (
            <>
              <RfAnalysisResults analysis={currentAnalysis} />
              <button
                type="button"
                onClick={() => changeAnalysis(null)}
                className="min-h-9 text-cyan underline"
              >
                Clear analysis
              </button>
            </>
          )}
        </div>
      )}
      <RfReferences preset={preset} />
      {onOverlayChange && mode === 'free-space' && (
        <div className="space-y-2 border-t border-line pt-3">
          {!origin && (
            <p className="text-muted">Place a transmitter to show the estimate on the map.</p>
          )}
          {mapError && (
            <p role="status" className="text-amber-300">
              {mapError}
            </p>
          )}
          <button
            type="button"
            disabled={!estimate}
            onClick={() => onOverlayChange(estimate)}
            className="min-h-10 w-full rounded border border-purple-300/40 bg-purple-300/10 px-3 text-purple-200 disabled:opacity-40"
          >
            {overlayVisible ? 'Update map estimate' : 'Show estimate on map'}
          </button>
          {overlayVisible && (
            <button
              type="button"
              onClick={() => onOverlayChange(null)}
              className="min-h-9 w-full text-muted"
            >
              Clear map estimate
            </button>
          )}
          <p className="text-muted">
            Purple outline: ideal distance limit. Straight path: transmitter to receiver. No terrain
            or measured coverage data. Changing inputs clears the previous estimate.
          </p>
        </div>
      )}
    </section>
  );
}
