/** Map style controls for the dated NASA GIBS imagery layer. */
import { useId } from 'react';

import { useNow } from '@/lib/hooks/useNow';

import {
  DAILY_IMAGERY_PRODUCTS,
  dailyImageryDateRange,
  type DailyImageryProductId,
} from '@/lib/map/dailyImagery';

import { GibsCredit, formatImageryDate } from './DailyImageryAttribution';
import { selectDailyImagery, useDailyImageryStore } from './dailyImageryStore';
import { sourceUnavailable, useMapSourcePolicy } from '@/lib/map/sourcePolicy';

export function DailyImageryControls() {
  const policy = useMapSourcePolicy();
  const reason = sourceUnavailable(policy, 'map:nasa_gibs_daily');
  const id = useId();
  const state = useDailyImageryStore();
  const now = useNow();
  const { min, max } = dailyImageryDateRange(state.product, now);
  const valid = selectDailyImagery(state, now) !== null;
  return (
    <section aria-labelledby={`${id}-title`} className="map-tool-section mt-4">
      <div className="flex items-start gap-2">
        <h3 id={`${id}-title`} className="map-tool-section-title min-w-0 flex-1">
          Daily satellite imagery
        </h3>
        <button
          type="button"
          role="switch"
          aria-checked={state.enabled && !reason}
          disabled={Boolean(reason)}
          aria-label="Daily satellite imagery"
          onClick={() => {
            if (!reason) state.setEnabled(!state.enabled);
          }}
          className="map-tool-text-button shrink-0 px-2"
        >
          <span className="map-tool-switch-track" aria-hidden="true" />
        </button>
      </div>
      <p className="map-tool-help">
        NASA true-colour daily composites for a chosen date, to check clouds, smoke plumes, floods
        and burn scars beside FIRMS detections. Off by default.
      </p>
      {reason && <p role="status" className="map-tool-help">{reason}</p>}
      {state.enabled && !reason && (
        <>
          <label className="map-tool-field">
            <span>Imagery product</span>
            <select
              className="map-tool-input"
              value={state.product}
              onChange={(event) => {
                state.setProduct(event.target.value as DailyImageryProductId);
              }}
            >
              {DAILY_IMAGERY_PRODUCTS.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.label}
                </option>
              ))}
            </select>
          </label>
          <label className="map-tool-field">
            <span>Imagery date (UTC)</span>
            <input
              type="date"
              className="map-tool-input"
              min={min}
              max={max}
              value={state.date}
              aria-invalid={!valid}
              aria-describedby={valid ? undefined : `${id}-date-error`}
              onChange={(event) => {
                state.setDate(event.target.value);
              }}
            />
          </label>
          {!valid && (
            <p id={`${id}-date-error`} className="map-tool-notice">
              Choose a date from {formatImageryDate(min)} to {formatImageryDate(max)}. Nothing is
              requested until the date is valid.
            </p>
          )}
          <p role="status" className={state.failed ? 'map-tool-notice' : 'sr-only'}>
            {state.failed
              ? 'Some imagery tiles did not load for this date. The base map stays visible; try another date or product.'
              : ''}
          </p>
          <p className="map-tool-help">
            Coarse imagery, roughly 250 m to 1 km per pixel: it shows weather-scale change, not
            buildings or vehicles. Tiles stop at zoom 9 and are enlarged beyond it. Gaps between
            orbital swaths, cloud and missing polar areas are normal, and today&apos;s image may
            still be filling in.
          </p>
          <p className="map-tool-help">
            Drawn on both the globe and the flat map, above the base map and beneath borders and
            labels. Like other web map imagery it ends near 85 degrees latitude.
          </p>
          <p className="map-tool-help">
            <GibsCredit /> Tiles load directly from NASA, which receives your network address and
            the areas you view.
          </p>
        </>
      )}
    </section>
  );
}
