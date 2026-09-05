/** Direction: areas of interest and collection plans with the evidence gathered against them. */
import { z } from 'zod';

import { categorySchema, liveEventSchema } from './eventSchemas';
import { apiCall, apiSend } from './client';

export const aoiSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  kind: z.string(),
  bbox: z.array(z.number()).nullable(),
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
  sirs: z.array(
    z.object({ code: z.string(), text: z.string(), events: z.array(liveEventSchema) }),
  ),
});
export type PlanEvidence = z.infer<typeof planEvidenceSchema>;

export interface AoiRequest {
  name: string;
  description?: string;
  kind: 'bbox' | 'countries';
  bbox?: [number, number, number, number];
  countries?: string[];
}

export interface SirRequest {
  text: string;
  keywords?: string[];
  categories?: z.infer<typeof categorySchema>[];
}

export interface PlanRequest {
  name: string;
  description?: string;
  aoi_id?: string | null;
  countries?: string[];
  pirs: { text: string; sirs: SirRequest[] }[];
  enabled?: boolean;
}

export async function fetchAois(): Promise<AreaOfInterest[]> {
  const page = await apiCall('/api/direction/aois', {
    schema: z.object({ items: z.array(aoiSchema) }),
  });
  return page.items;
}

export function createAoi(request: AoiRequest): Promise<AreaOfInterest> {
  return apiCall('/api/direction/aois', { method: 'POST', body: request, schema: aoiSchema });
}

export function deleteAoi(id: string): Promise<void> {
  return apiSend(`/api/direction/aois/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export async function fetchPlans(): Promise<CollectionPlan[]> {
  const page = await apiCall('/api/direction/plans', {
    schema: z.object({ items: z.array(planSchema) }),
  });
  return page.items;
}

export function createPlan(request: PlanRequest): Promise<CollectionPlan> {
  return apiCall('/api/direction/plans', { method: 'POST', body: request, schema: planSchema });
}

export function fetchPlanEvidence(id: string): Promise<PlanEvidence> {
  return apiCall(`/api/direction/plans/${encodeURIComponent(id)}`, { schema: planEvidenceSchema });
}

export function deletePlan(id: string): Promise<void> {
  return apiSend(`/api/direction/plans/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
