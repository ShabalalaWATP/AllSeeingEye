import { z } from 'zod';

import { scopedMutation } from '@/lib/workspaceAccess';

import { apiCall } from './client';
import type { components } from './types.gen';

export type TeamCopyPreview = components['schemas']['TeamCopyPreviewOut'];
export type TeamCopyResult = components['schemas']['TeamCopyOut'];
export type TeamCopyProvenance = components['schemas']['TeamCopyProvenanceOut'];
export type TeamCopyOmission = components['schemas']['TeamCopyOmission'];

const omissionSchema = z.enum([
  'research_brief',
  'claim_generation',
  'original_passages',
  'source_assessment',
  'scope_references',
]) satisfies z.ZodType<TeamCopyOmission>;

const previewSchema = z.object({
  team_id: z.string(),
  team_name: z.string(),
  source_version_number: z.number().int().positive(),
  private_inputs: z.array(
    z.object({ label: z.string(), title: z.string(), source_id: z.string() }),
  ),
  omissions: z.array(omissionSchema),
  omitted_scope_keys: z.array(z.string()),
  not_copied: z.object({
    claims: z.number().int().nonnegative(),
    original_files: z.number().int().nonnegative(),
    original_passages: z.number().int().nonnegative(),
    reviewed_snapshots: z.number().int().nonnegative(),
    map_views: z.number().int().nonnegative(),
  }),
  content_sha256: z.string(),
  existing_report_id: z.string().nullable(),
}) satisfies z.ZodType<TeamCopyPreview>;

const resultSchema = z.object({
  report_id: z.string(),
  version_number: z.number().int().positive(),
  team_id: z.string(),
  copied_at: z.string(),
  created: z.boolean(),
}) satisfies z.ZodType<TeamCopyResult>;

const provenanceSchema = z.object({
  report_id: z.string(),
  team_id: z.string(),
  copied_by: z.string(),
  copied_by_name: z.string().nullable(),
  copied_at: z.string(),
  source_version_number: z.number().int().positive(),
  source_report_id: z.string().nullable(),
  content_sha256: z.string(),
  disclosed_private_inputs: z.number().int().nonnegative(),
  omissions: z.array(omissionSchema),
}) satisfies z.ZodType<TeamCopyProvenance>;

const versionPath = (reportId: string, version: number) =>
  `/api/reports/${encodeURIComponent(reportId)}/versions/${version}`;

export function fetchTeamCopyPreview(
  reportId: string,
  version: number,
  teamId: string,
  signal: AbortSignal,
): Promise<TeamCopyPreview> {
  const query = new URLSearchParams({ team_id: teamId });
  return apiCall(`${versionPath(reportId, version)}/team-copy-preview?${query.toString()}`, {
    schema: previewSchema,
    signal,
  });
}

/** Retrying returns the existing copy; the server never publishes a version twice. */
export function copyReportToTeam(
  reportId: string,
  version: number,
  body: { team_id: string; disclosed_evidence_labels: string[] },
  signal: AbortSignal,
): Promise<TeamCopyResult> {
  return scopedMutation(() =>
    apiCall(`${versionPath(reportId, version)}/team-copies`, {
      method: 'POST',
      body,
      signal,
      schema: resultSchema,
    }),
  );
}

export function fetchTeamCopyProvenance(
  reportId: string,
  signal: AbortSignal,
): Promise<TeamCopyProvenance> {
  return apiCall(`/api/reports/${encodeURIComponent(reportId)}/team-copy-provenance`, {
    schema: provenanceSchema,
    signal,
  });
}
