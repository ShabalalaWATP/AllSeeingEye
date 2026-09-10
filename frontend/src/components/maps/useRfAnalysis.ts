import { useCallback, useEffect, useState } from 'react';
import type { Position } from '@/lib/map/geoJsonTypes';
import type { RfInputs } from '@/lib/map/rfPlanning';
import { calculateRf } from '@/lib/map/rfPlanning';
import { parseRfEngineering } from '@/lib/map/rfEngineering';
import { measure, measurementPoint } from '@/lib/map/measurements';
import { RF_ENVIRONMENT_DEFAULTS, type RfDraft } from '@/lib/map/rfDraft';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import {
  createRfTerrainPath,
  createRfTerrainRadials,
  type RfTerrainSamplePlan,
} from '@/lib/map/rfTerrainSampling';
import { createAutomaticTerrainPlan, resolveRfMode, rfStudyRadius } from '@/lib/map/rfAutomation';
import { runRfTerrainStudy } from '@/lib/map/rfTerrainStudy';
import { calculateHfSkywave } from '@/lib/map/hfSkywave';
import { calculateGroundwave } from '@/lib/api/groundwave';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useRfTerrainCache } from './useRfTerrainCache';

interface PendingAnalysis {
  identity: string;
  authority: ReturnType<typeof useScopedRequest>;
  signal: AbortSignal;
  busy: boolean;
  error: string | null;
  progress: string | null;
}
function number(value: unknown, label: string): number {
  if (typeof value !== 'string' || !value.trim() || !Number.isFinite(Number(value)))
    throw new Error(`Enter a valid ${label}.`);
  return Number(value);
}
function bounded(value: number, min: number, max: number, label: string): number {
  if (!Number.isFinite(value) || value < min || value > max)
    throw new Error(`${label}: enter a value from ${min} to ${max}.`);
  return value;
}

/** Caller-triggered analysis. Input, position, panel and authority changes cancel stale work. */
export function useRfAnalysis(
  input: RfInputs,
  draft: RfDraft,
  origin: Position | null,
  receiver: Position | null,
  onChange: (value: RfAnalysis | null) => void,
) {
  const request = useScopedRequest();
  const cache = useRfTerrainCache();
  const [pending, setPending] = useState<PendingAnalysis | null>(null);
  const identity = JSON.stringify([input, draft, origin, receiver]);
  useEffect(() => {
    request();
  }, [identity, request]);
  const cancel = useCallback(() => {
    request();
  }, [request]);
  async function analyse() {
    const signal = request();
    const cancel = () =>
      setPending((previous) =>
        previous?.signal === signal
          ? { ...previous, busy: false, error: null, progress: null }
          : previous,
      );
    signal.addEventListener('abort', cancel, { once: true });
    setPending({ identity, authority: request, signal, busy: true, error: null, progress: null });
    const progress = (message: string) =>
      setPending((previous) =>
        previous?.signal === signal && !signal.aborted
          ? { ...previous, progress: message }
          : previous,
      );
    let validated = false;
    try {
      signal.throwIfAborted();
      onChange(null);
      if (!origin) throw new Error('Place a transmitter on the map first.');
      measurementPoint(...origin);
      if (receiver) measurementPoint(...receiver);
      const env = { ...RF_ENVIRONMENT_DEFAULTS, ...draft.environment };
      const mode = resolveRfMode(draft);
      let value: RfAnalysis;
      if (mode === 'terrain') {
        if (input.frequencyMHz < 30)
          throw new Error('Choose an HF mode for frequencies below 30 MHz.');
        if (draft.study === 'link' && !receiver)
          throw new Error('Place a receiver to analyse a point-to-point link.');
        const target = draft.study === 'area' ? null : receiver;
        const automatic = !target && draft.radiusMode === 'automatic';
        let requestedRadiusKm: number | null = null;
        let plan: RfTerrainSamplePlan;
        if (target) plan = createRfTerrainPath(origin, target);
        else {
          requestedRadiusKm = rfStudyRadius(input, draft);
          plan = automatic
            ? createAutomaticTerrainPlan(origin, requestedRadiusKm)
            : createRfTerrainRadials(origin, requestedRadiusKm);
        }
        // The sampled path defines its distance; a hidden free-space distance is irrelevant.
        const engineering = parseRfEngineering(draft.engineering, mode);
        calculateRf({ ...input, distanceKm: plan.maxDistanceKm }, engineering);
        validated = true;
        value = await runRfTerrainStudy({
          input,
          engineering,
          plan,
          refine: automatic,
          cache,
          signal,
          onProgress: progress,
        });
        if (automatic && requestedRadiusKm !== null && plan.maxDistanceKm < requestedRadiusKm) {
          value = {
            ...value,
            terrain: {
              ...value.terrain,
              warnings: [
                `The initial automatic radius was reduced from ${requestedRadiusKm.toFixed(1)} to ${plan.maxDistanceKm.toFixed(1)} km to fit the supported terrain tile and latitude limits. The displayed radius is the area actually screened.`,
                ...value.terrain.warnings,
              ],
            },
          };
        }
      } else if (mode === 'hf-groundwave') {
        const engineering = parseRfEngineering(draft.engineering, mode);
        bounded(input.sensitivityDbm, -200, 0, 'Receiver sensitivity (dBm)');
        if (draft.study === 'link' && !receiver)
          throw new Error('Place a receiver to analyse a point-to-point link.');
        const target = draft.study === 'area' ? null : receiver;
        const radiusKm = target
          ? Math.max(
              2,
              bounded(
                measure([origin, target], 'distance').metres / 1000,
                1,
                200,
                'Groundwave receiver distance (km)',
              ),
            )
          : rfStudyRadius(input, draft);
        const body = {
          frequency_mhz: bounded(input.frequencyMHz, 1.6, 30, 'HF frequency (MHz)'),
          tx_power_w:
            10 **
            ((bounded(input.transmitDbm, 0, 80, 'Groundwave transmit power (dBm)') - 30) / 10),
          tx_height_m: bounded(input.transmitHeightM, 0, 50, 'Transmitter height (m AGL)'),
          rx_height_m: bounded(input.receiveHeightM, 0, 50, 'Receiver height (m AGL)'),
          conductivity_sm: bounded(
            number(env.conductivitySm, 'ground conductivity'),
            0.00001,
            10,
            'Conductivity (S/m)',
          ),
          relative_permittivity: bounded(
            number(env.permittivity, 'relative permittivity'),
            1,
            100,
            'Relative permittivity',
          ),
          surface_refractivity: bounded(
            number(env.refractivity, 'surface refractivity'),
            250,
            400,
            'Surface refractivity',
          ),
          tx_gain_dbi: bounded(input.transmitGainDbi, -30, 30, 'Transmitter gain (dBi)'),
          rx_gain_dbi: bounded(input.receiveGainDbi, -30, 30, 'Receiver gain (dBi)'),
          system_loss_db: bounded(input.lossesDb, 0, 120, 'Combined system loss (dB)'),
          max_distance_km: bounded(radiusKm, 2, 200, 'Groundwave radius (km)'),
          sample_count: 48,
        };
        validated = true;
        progress('Calculating groundwave');
        const result = await calculateGroundwave(body, signal);
        signal.throwIfAborted();
        value = { kind: mode, result, origin, receiver: target, input, engineering };
      } else if (mode === 'hf-skywave') {
        // This geometry-only scenario has no received-power or free-space distance calculation.
        const scenario = calculateHfSkywave({
          frequencyMHz: input.frequencyMHz,
          criticalFrequencyMHz: number(env.criticalFrequencyMHz, 'critical frequency'),
          virtualHeightKm: number(env.virtualHeightKm, 'virtual layer height'),
          minElevationDeg: number(env.minElevationDeg, 'minimum launch elevation'),
          maxElevationDeg: number(env.maxElevationDeg, 'maximum launch elevation'),
        });
        value = { kind: mode, estimate: { origin, frequencyMHz: input.frequencyMHz, scenario } };
      } else throw new Error('Use Show estimate on map for the free-space reference.');
      signal.throwIfAborted();
      onChange(value);
    } catch (reason) {
      if (!signal.aborted)
        setPending((previous) =>
          previous?.signal === signal
            ? {
                ...previous,
                error:
                  !validated && reason instanceof Error ? reason.message : describeError(reason),
              }
            : previous,
        );
    } finally {
      signal.removeEventListener('abort', cancel);
      setPending((previous) =>
        previous?.signal === signal ? { ...previous, busy: false, progress: null } : previous,
      );
    }
  }
  const current =
    pending?.identity === identity && pending.authority === request && !pending.signal.aborted;
  return {
    analyse,
    cancel,
    busy: current && pending.busy,
    error: current ? pending.error : null,
    progress: current ? pending.progress : null,
  };
}
