/** Direction: areas of interest and collection plans with the evidence gathered against them. */
import { z } from 'zod';
import { frozenAreaSchema } from './areaSchemas';

import { scopedMutation } from '@/lib/workspaceAccess';
import type { components } from './types.gen';

import { liveEventSchema } from './eventSchemas';
import { apiCall, apiSend } from './client';

export const aoiSchema = z.object({
  team_id: z.uuid().nullable(),
  id: z.string(),
  name: z.string(),
  description: z.string(),
  kind: z.string(),
  bbox: z.array(z.number()).nullable(),
  research_area: frozenAreaSchema.nullable().optional(),
  countries: z.array(z.string()),
  created_by: z.string(),
  created_at: z.string(),
});
export type AreaOfInterest = z.infer<typeof aoiSchema>;

export const sirSchema = z.object({
  code: z.string(),
  text: z.string(),
  keywords: z.array(z.string()),
  categories: z.array(z.string()),
});
export type Sir = z.infer<typeof sirSchema>;

export const pirSchema = z.object({
  code: z.string(),
  text: z.string(),
  sirs: z.array(sirSchema),
});
export type Pir = z.infer<typeof pirSchema>;

export const planSchema = z.object({
  team_id: z.uuid().nullable(),
  id: z.string(),
  name: z.string(),
  description: z.string(),
  aoi_id: z.string().nullable(),
  countries: z.array(z.string()),
  pirs: z.array(pirSchema),
  enabled: z.boolean(),
  created_by: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type CollectionPlan = z.infer<typeof planSchema>;

export const planEvidenceSchema = z.object({
  plan: planSchema,
  aoi: aoiSchema.nullable(),
  considered: z.number().int(),
  sirs: z.array(z.object({ code: z.string(), text: z.string(), events: z.array(liveEventSchema) })),
});
export type PlanEvidence = z.infer<typeof planEvidenceSchema>;

export type AoiRequest = components['schemas']['AoiIn'];

export type SirRequest = components['schemas']['SirIn'];

export type PlanRequest = components['schemas']['PlanIn'];

export type PlanUpdateRequest = components['schemas']['PlanUpdateIn'];

export async function fetchAois(): Promise<AreaOfInterest[]> {
  const page = await apiCall('/api/direction/aois', {
    schema: z.object({ items: z.array(aoiSchema) }),
  });
  return page.items;
}

export function createAoi(request: AoiRequest): Promise<AreaOfInterest> {
  return scopedMutation(() =>
    apiCall('/api/direction/aois', { method: 'POST', body: request, schema: aoiSchema }),
  );
}

export function deleteAoi(id: string): Promise<void> {
  return scopedMutation(() =>
    apiSend(`/api/direction/aois/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  );
}

export async function fetchPlans(): Promise<CollectionPlan[]> {
  const page = await apiCall('/api/direction/plans', {
    schema: z.object({ items: z.array(planSchema) }),
  });
  return page.items;
}

export function createPlan(request: PlanRequest): Promise<CollectionPlan> {
  return scopedMutation(() =>
    apiCall('/api/direction/plans', { method: 'POST', body: request, schema: planSchema }),
  );
}

/** Saves an edit made from `expected_updated_at`; a newer revision answers 409 conflict. */
export function updatePlan(id: string, request: PlanUpdateRequest): Promise<CollectionPlan> {
  return scopedMutation(() =>
    apiCall(`/api/direction/plans/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: request,
      schema: planSchema,
    }),
  );
}

/** The plan's requirements and revision without gathering live evidence. */
export function fetchPlan(id: string, signal?: AbortSignal): Promise<CollectionPlan> {
  return apiCall(`/api/direction/plans/${encodeURIComponent(id)}/definition`, {
    schema: planSchema,
    ...(signal ? { signal } : {}),
  });
}

export function fetchPlanEvidence(id: string): Promise<PlanEvidence> {
  return apiCall(`/api/direction/plans/${encodeURIComponent(id)}`, { schema: planEvidenceSchema });
}

export function deletePlan(id: string): Promise<void> {
  return scopedMutation(() =>
    apiSend(`/api/direction/plans/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  );
}

export const planMapMatchesSchema = z.object({
  plan: planSchema,
  window_hours: z.number().int(),
  pool_limit: z.number().int(),
  per_requirement_limit: z.number().int(),
  considered: z.number().int(),
  truncated: z.boolean(),
  matches: z.array(z.object({ event_id: z.string(), codes: z.array(z.string()) })),
});
export type PlanMapMatches = z.infer<typeof planMapMatchesSchema>;

/** A bounded, on-demand sample of live events matching one readable plan; never streamed. */
export function fetchPlanMapMatches(id: string, signal?: AbortSignal): Promise<PlanMapMatches> {
  return apiCall(`/api/direction/plans/${encodeURIComponent(id)}/map-matches`, {
    schema: planMapMatchesSchema,
    ...(signal ? { signal } : {}),
  });
}
