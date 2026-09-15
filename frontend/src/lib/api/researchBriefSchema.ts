import { z } from 'zod';

const id = z.uuid();
const optionalId = id.nullable();
const date = z.iso.datetime({ offset: true });
const optionalDate = date.nullable();
const boundedId = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/);
const opaqueObject = z.record(z.string(), z.unknown());

export const requirementSchema = z.object({
  id: boundedId,
  question: z.string().min(1).max(500),
  required: z.boolean(),
  priority: z.number().int().min(1).max(12),
});
export type BriefRequirement = z.infer<typeof requirementSchema>;

const identitySchema = z.object({
  id,
  revision: z.number().int().positive(),
  owner_id: id,
  team_id: optionalId,
  title: z.string().min(1).max(120),
  created_at: date,
  revised_at: date,
  preset_id: boundedId.nullable(),
  preset_version: z.number().int().positive().nullable(),
  schema_version: z.literal(1),
  origin: z.enum(['authored', 'legacy-derived']),
  published: z.boolean(),
});

const questionSchema = z.object({
  main: z.string().min(1).max(2000),
  requirements: z.array(requirementSchema).max(12),
  exclusions: z.array(z.string().min(1).max(300)).max(10),
});

const scopeSchema = z.object({
  country_isos: z.array(z.string().regex(/^[A-Z]{2}$/)).max(8),
  focus: z.enum(['general', 'company', 'domain', 'document', 'media']),
  subject: z.string().nullable(),
  reviewed_aliases: z.array(z.string()),
  conflict_id: z.string().nullable(),
  hazard: z.string().nullable(),
  categories: z.array(z.string()),
  area: opaqueObject.nullable(),
  map_origin: opaqueObject.nullable(),
  map_view_id: optionalId,
  map_revision_id: optionalId,
  disclose_area_to_provider: z.boolean(),
  plan_id: optionalId,
  parent_report_id: optionalId,
  parent_version: z.number().int().positive().nullable(),
  origin_report_id: optionalId,
  origin_version: z.number().int().positive().nullable(),
});

const observationSchema = z.object({
  policy: z.enum(['explicit', 'relative', 'template_default']),
  since: optionalDate,
  until: optionalDate,
  lookback_hours: z.number().int().positive().nullable(),
  time_basis: z.enum(['publication', 'acquisition_or_publication', 'recorded_time']).nullable(),
  forecast_horizon_days: z.number().int().min(1).max(366).nullable(),
});

const lensSchema = z.object({
  id: z.enum([
    'general',
    'uk_policy',
    'civilian_protection',
    'regional_security',
    'economic_exposure',
    'energy_security',
    'supply_chain',
    'defensive_cyber',
    'actor_perspective',
  ]),
  audience: z.string().nullable(),
  decision_need: z.string().nullable(),
  relevance_instructions: z.string().nullable(),
  challenge_conclusions: z.boolean(),
});

const collectionSchema = z.object({
  languages: z.array(z.string()).min(1).max(8),
  terms: z.array(z.string()).nullable(),
  query_variants: z.array(opaqueObject),
  source_policy: z.enum(['all_eligible', 'selected_only']),
  source_ids: z.array(z.string()).nullable(),
  web_search: z.boolean(),
  candidate_hypotheses: z.array(opaqueObject),
  planned_tasks: z.array(opaqueObject),
  require_primary: z.boolean(),
  require_local: z.boolean(),
  require_opposition: z.boolean(),
});

const outputSchema = z.object({
  depth: z.enum(['quick', 'detailed', 'advanced']),
  language: z.string(),
  style: z.enum(['briefing', 'assessment']),
  template_id: boundedId,
  preferred_sections: z.array(boundedId).max(16),
  chart_preference: z.enum(['auto', 'prefer', 'avoid']),
  table_preference: z.enum(['auto', 'prefer', 'avoid']),
  model_profile_id: optionalId,
});

const limitsSchema = z.object({
  policy_id: boundedId,
  max_passes: z.number().int().positive().nullable(),
  max_external_operations: z.number().int().positive().nullable(),
  max_model_calls: z.number().int().positive().nullable(),
  max_output_tokens: z.number().int().positive().nullable(),
  max_collection_seconds: z.number().int().positive().nullable(),
});

const monitoringSchema = z.object({
  indicators: z.array(z.object({ id: boundedId, condition: z.string().min(1).max(500) })),
  review_conditions: z.array(z.string()),
  prefer_novelty: z.boolean().nullable(),
  organisation_profile_id: optionalId,
});

const privateInputSchema = z.object({
  kind: z.enum(['session', 'durable_report']),
  input_id: optionalId,
  report_id: optionalId,
  report_version: z.number().int().positive().nullable(),
  expires_at: optionalDate,
  disclose_to_provider: z.boolean(),
});

export const briefDefinitionSchema = z.object({
  question: questionSchema,
  scope: scopeSchema,
  observation: observationSchema,
  lens: lensSchema,
  collection: collectionSchema,
  output: outputSchema,
  limits: limitsSchema,
  monitoring: monitoringSchema,
  private_inputs: z.array(privateInputSchema).max(8),
});
export const researchBriefSchema = briefDefinitionSchema.extend({ identity: identitySchema });
export const briefDraftSchema = briefDefinitionSchema.extend({
  title: z.string().min(1).max(120),
  team_id: optionalId,
  preset_id: boundedId.nullable(),
  preset_version: z.number().int().positive().nullable(),
});
export type ResearchBrief = z.infer<typeof researchBriefSchema>;
export type BriefDraft = z.infer<typeof briefDraftSchema>;

export const briefSummarySchema = identitySchema.pick({
  id: true,
  revision: true,
  owner_id: true,
  team_id: true,
  title: true,
  schema_version: true,
  origin: true,
  published: true,
  created_at: true,
  revised_at: true,
});
export type BriefSummary = z.infer<typeof briefSummarySchema>;
