import { z } from 'zod';

import { apiCall } from './client';
import { briefDraftSchema, type BriefDraft } from './researchBriefSchema';

const id = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/);
const group = z.enum(['conflict', 'cyber', 'economy', 'cross_cutting']);
const lens = z.enum([
  'general',
  'uk_policy',
  'civilian_protection',
  'regional_security',
  'economic_exposure',
  'energy_security',
  'supply_chain',
  'defensive_cyber',
  'actor_perspective',
]);
const depth = z.enum(['quick', 'detailed', 'advanced']);

const presetSchema = z.object({
  id,
  version: z.number().int().positive(),
  title: z.string().min(1),
  purpose: z.string().min(1),
  group,
  reviewed_on: z.string(),
  question: z.string().min(1),
  requirements: z
    .array(
      z.object({
        id,
        question: z.string().min(1),
        required: z.boolean(),
        priority: z.number().int().min(1).max(12),
      }),
    )
    .min(1)
    .max(6),
  required_inputs: z.array(
    z.object({
      id,
      label: z.string(),
      guidance: z.string(),
      target: id,
      required: z.boolean(),
    }),
  ),
  scope_note: z.string(),
  suggested_languages: z.array(z.string()),
  language_note: z.string(),
  source_bundles: z.array(id),
  lens_choices: z.array(lens),
  default_lens: lens,
  default_depth: depth,
  keywords: z.array(z.string()),
});

const readinessSchema = z.object({
  policy_version: z.string(),
  source_bundles: z.array(
    z.object({
      id,
      candidate_provider_ids: z.array(id),
      gap_ids: z.array(id),
      status: z.enum(['unverified_candidates', 'declared_gaps', 'unavailable']),
    }),
  ),
  sources: z.array(
    z.object({
      id,
      name: z.string(),
      readiness: z.enum([
        'public_unverified',
        'configured_unverified',
        'requirement_unknown',
        'requirement_missing',
        'disabled',
      ]),
      candidate: z.boolean(),
      scope_language_compatible: z.boolean(),
      constraints: z.string(),
      limitations: z.array(z.string()),
    }),
  ),
  gaps: z.array(z.object({ id, name: z.string(), reason: z.string() })),
  languages: z.array(
    z.object({
      language: z.string(),
      status: z.enum(['configured_route_unverified', 'no_configured_route']),
      source_ids: z.array(id),
      note: z.string(),
    }),
  ),
  candidate_provider_ids: z.array(id),
  source_selection_required: z.boolean(),
  required_input_ids: z.array(id),
  note: z.string(),
});

const presetItemSchema = z.object({ preset: presetSchema, readiness: readinessSchema });
const presetPageSchema = z.object({
  schema_version: z.literal(1),
  items: z.array(presetItemSchema).max(20),
  lens_choices: z.array(lens),
  lens_rule: z.string(),
});
const definitionSchema = z.object({
  definition: briefDraftSchema,
  readiness: readinessSchema,
  omitted_requirement_ids: z.array(id),
  note: z.string(),
});

export type PresetItem = z.infer<typeof presetItemSchema>;
export type PresetGroup = z.infer<typeof group>;
export type PresetLens = z.infer<typeof lens>;
export type PresetDepth = z.infer<typeof depth>;

export function fetchResearchPresets(signal: AbortSignal) {
  return apiCall('/api/research/presets', { schema: presetPageSchema, signal });
}

export function editablePresetDefinition(
  item: PresetItem,
  choices: {
    depth: PresetDepth;
    lens: PresetLens;
    selectedRequirementIds: string[];
    selectedSourceIds?: string[];
  },
  signal: AbortSignal,
) {
  return apiCall(`/api/research/presets/${encodeURIComponent(item.preset.id)}/definition`, {
    method: 'POST',
    body: {
      version: item.preset.version,
      depth: choices.depth,
      lens: choices.lens,
      selected_requirement_ids: choices.selectedRequirementIds,
      ...(choices.selectedSourceIds ? { selected_source_ids: choices.selectedSourceIds } : {}),
    },
    schema: definitionSchema,
    signal,
    retryAfterRefresh: false,
  });
}

/** Required starter inputs remain explicit even though a partial brief can be saved. */
export function missingPresetInputs(item: PresetItem, draft: BriefDraft): string[] {
  return item.preset.required_inputs
    .filter((input) => {
      if (!input.required) return false;
      switch (input.target) {
        case 'scope.subject':
          return !draft.scope.subject?.trim();
        case 'scope.country_isos':
          return draft.scope.country_isos.length === 0;
        case 'scope.hazard':
          return !draft.scope.hazard?.trim();
        case 'scope.area':
          return !draft.scope.area && !draft.scope.map_origin && !draft.scope.map_view_id;
        case 'question.main':
          return !draft.question.main.trim() || draft.question.main === item.preset.question;
        default:
          return true;
      }
    })
    .map((input) => input.label);
}
