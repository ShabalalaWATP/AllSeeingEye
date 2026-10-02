import { z } from 'zod';
import { scopedMutation } from '@/lib/workspaceAccess';
import { apiCall } from './client';
import { countsSchema, forecastSchema, watchSchema } from './forecastSchemas';
import type { components } from './types.gen';

export type ForecastCreate = components['schemas']['ForecastCreateIn'];
export type ForecastReview = components['schemas']['ForecastReviewIn'];
export type OutcomeEvidence = components['schemas']['OutcomeEvidenceIn'];
export type ForecastSupersession = components['schemas']['ForecastSupersessionIn'];
const root = (id: string, version: number) =>
  `/api/reports/${encodeURIComponent(id)}/versions/${version}/ledgers`;
export async function listForecasts(
  id: string,
  version: number,
  offset: number,
  signal: AbortSignal,
) {
  const page = await apiCall(`${root(id, version)}?limit=20&offset=${offset}`, {
    signal,
    schema: z.object({
      items: z.array(
        z
          .object({
            anchor: z.object({ kind: z.enum(['forecast', 'indicator']) }).loose(),
            history: z.unknown(),
          })
          .loose(),
      ),
      total: z.number().int(),
      offset: z.number().int(),
      limit: z.number().int(),
    }),
  });
  // Indicators share this ledger endpoint, but the panel only renders validated forecasts.
  return {
    ...page,
    items: page.items
      .filter((row) => row.anchor.kind === 'forecast')
      .map((row) => forecastSchema.parse(row)),
  };
}
export function createForecast(
  id: string,
  version: number,
  body: ForecastCreate,
  signal: AbortSignal,
) {
  return scopedMutation(() =>
    apiCall(`${root(id, version)}/forecasts`, {
      method: 'POST',
      body,
      signal,
      schema: forecastSchema,
    }),
  );
}
export function reviewForecast(
  id: string,
  version: number,
  ledger: string,
  body: ForecastReview,
  signal: AbortSignal,
) {
  return scopedMutation(() =>
    apiCall(`${root(id, version)}/${encodeURIComponent(ledger)}/reviews`, {
      method: 'POST',
      body,
      signal,
      schema: forecastSchema,
    }),
  );
}
export function supersedeForecast(
  id: string,
  version: number,
  ledger: string,
  body: ForecastSupersession,
  signal: AbortSignal,
) {
  return scopedMutation(() =>
    apiCall(`${root(id, version)}/${encodeURIComponent(ledger)}/supersessions`, {
      method: 'POST',
      body,
      signal,
      schema: forecastSchema,
    }),
  );
}
export function exportForecasts(id: string, version: number, ids: string[], signal: AbortSignal) {
  return apiCall(`${root(id, version)}/exports/forecasts`, {
    method: 'POST',
    body: { ledger_ids: ids },
    signal,
    schema: z.array(forecastSchema).min(1).max(20),
  });
}
export function forecastWatches(teamId: string, offset: number, signal: AbortSignal) {
  const query = new URLSearchParams({ limit: '20', offset: String(offset) });
  query.set(teamId ? 'team_id' : 'personal', teamId || 'true');
  return apiCall(`/api/forecasts/watches?${query}`, {
    signal,
    schema: z.object({
      items: z.array(watchSchema),
      total: z.number().int(),
      limit: z.number().int(),
      offset: z.number().int(),
    }),
  });
}
export function forecastCounts(teamId: string, since: string, until: string, signal: AbortSignal) {
  const query = new URLSearchParams({ since, until });
  query.set(teamId ? 'team_id' : 'personal', teamId || 'true');
  return apiCall(`/api/forecasts/counts?${query}`, { signal, schema: countsSchema });
}
