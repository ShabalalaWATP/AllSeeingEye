import { useState } from 'react';
import { calculateRf, RF_FIELDS } from '@/lib/map/rfPlanning';
import type { RfInputs } from '@/lib/map/rfPlanning';
import { RF_PRESETS } from '@/lib/map/rfPresets';
import { rfMapEstimate } from '@/lib/map/rfMap';
import type { RfMapEstimate } from '@/lib/map/rfMap';
import type { Position } from '@/lib/map/geoJsonTypes';
import { measure } from '@/lib/map/measurements';
import { RfResults } from './RfResults';
import { createRfDraft } from '@/lib/map/rfDraft';
import type { RfDraft } from '@/lib/map/rfDraft';

const BASIC_FIELDS = new Set<keyof RfInputs>([
  'frequencyMHz',
  'transmitDbm',
  'transmitHeightM',
  'receiveHeightM',
  'distanceKm',
]);
export interface RfCalculatorPanelProps {
  measuredDistanceKm?: number | undefined;
  origin?: Position | null;
  receiver?: Position | null;
  picking?: 'origin' | 'receiver' | null;
  onPick?: (point: 'origin' | 'receiver' | null) => void;
  onOverlayChange?: (estimate: RfMapEstimate | null) => void;
  overlayVisible?: boolean;
  draft?: RfDraft;
  onDraftChange?: (draft: RfDraft) => void;
  onClearReceiver?: () => void;
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
}: RfCalculatorPanelProps) {
  const [localDraft, setLocalDraft] = useState(() => createRfDraft());
  const { values, presetId } = draft ?? localDraft;
  const setDraft = onDraftChange ?? setLocalDraft;
  const preset = RF_PRESETS.find((item) => item.id === presetId) ?? RF_PRESETS[0];
  const input = Object.fromEntries(
    Object.entries(values).map(([key, value]) => [key, value.trim() ? Number(value) : NaN]),
  ) as unknown as RfInputs;
  if (origin && receiver) input.distanceKm = measure([origin, receiver], 'distance').metres / 1000;
  let result: ReturnType<typeof calculateRf> | null = null;
  let estimate: RfMapEstimate | null = null;
  let error: string | null = null;
  let mapError: string | null = null;
  try {
    result = calculateRf(input);
    if (origin) {
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
    setDraft({ values: { ...values, [key]: value }, presetId: 'custom' });
    onOverlayChange?.(null);
  };
  const field = ({ key, label, min, max }: (typeof RF_FIELDS)[number]) => (
    <label key={key} className="block text-muted">
      {label}
      <input
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
          Choose a radio, place its transmitter, then compare an estimated range circle and optional
          receiver path.
        </p>
      </header>
      <label className="block text-muted">
        Radio preset
        <select
          value={presetId}
          onChange={(event) => {
            const selected = RF_PRESETS.find((item) => item.id === event.target.value);
            if (selected) {
              setDraft(createRfDraft(selected.values, selected.id));
              onOverlayChange?.(null);
            }
          }}
          className="mt-1 min-h-10 w-full rounded border border-line bg-ground px-2 text-text"
        >
          {RF_PRESETS.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <p className="text-muted">
        {preset?.note} Presets are illustrative, not equipment specifications or permission to
        transmit.
      </p>
      {onPick && (
        <div className="space-y-2 rounded border border-line bg-ground/50 p-3">
          <p className="font-mono uppercase tracking-wide text-muted">Position on map</p>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              aria-pressed={picking === 'origin'}
              onClick={() => onPick(picking === 'origin' ? null : 'origin')}
              className="min-h-10 rounded border border-line px-2 text-cyan"
            >
              {origin ? 'Move transmitter' : 'Place transmitter'}
            </button>
            <button
              type="button"
              aria-pressed={picking === 'receiver'}
              onClick={() => onPick(picking === 'receiver' ? null : 'receiver')}
              className="min-h-10 rounded border border-line px-2 text-cyan"
            >
              {receiver ? 'Move receiver' : 'Add receiver'}
            </button>
          </div>
          {picking && (
            <p role="status" className="text-cyan">
              Click the map to place the {picking === 'origin' ? 'transmitter' : 'receiver'}. Select
              the button again to cancel.
            </p>
          )}
          {origin && (
            <p className="font-mono text-muted">
              TX {origin[1].toFixed(4)}, {origin[0].toFixed(4)}
            </p>
          )}
          {receiver && (
            <p className="font-mono text-muted">
              RX {receiver[1].toFixed(4)}, {receiver[0].toFixed(4)}
            </p>
          )}
          {receiver && onClearReceiver && (
            <button
              type="button"
              onClick={onClearReceiver}
              className="min-h-9 text-muted underline"
            >
              Remove receiver, keep transmitter
            </button>
          )}
          {origin && receiver && (
            <p className="text-muted">Path length follows the two map positions.</p>
          )}
        </div>
      )}
      {measuredDistanceKm !== undefined &&
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
      <div className="grid grid-cols-2 gap-3">
        {RF_FIELDS.filter(({ key }) => BASIC_FIELDS.has(key)).map(field)}
      </div>
      <details className="rounded border border-line p-3">
        <summary className="cursor-pointer text-text">
          Antenna gains, losses and sensitivity
        </summary>
        <div className="mt-3 grid grid-cols-2 gap-3">
          {RF_FIELDS.filter(({ key }) => !BASIC_FIELDS.has(key)).map(field)}
        </div>
      </details>
      {error && (
        <p role="alert" className="text-amber-300">
          {error}
        </p>
      )}
      {result && <RfResults result={result} />}
      {onOverlayChange && (
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
