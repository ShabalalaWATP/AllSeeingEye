import type { CollectionPlan } from './api/direction';
import { briefDraftSchema, type BriefDraft, type ResearchBrief } from './api/researchBriefSchema';

export function validateBriefDraft(draft: BriefDraft): string | null {
  if (!draft.title.trim()) return 'Enter a brief title.';
  if (!draft.question.main.trim()) return 'Enter a research question.';
  const requirements = draft.question.requirements;
  if (new Set(requirements.map((row) => row.id)).size !== requirements.length)
    return 'Requirement IDs must be unique.';
  const required = requirements.filter((row) => row.required).length;
  const cap = { quick: 3, detailed: 6, advanced: 12 }[draft.output.depth];
  if (required > cap) return `This depth allows at most ${cap} required questions.`;
  if (
    draft.observation.policy === 'explicit' &&
    (!draft.observation.since ||
      !draft.observation.until ||
      Date.parse(draft.observation.since) >= Date.parse(draft.observation.until))
  )
    return 'Choose a positive exact UTC observation interval.';
  if (
    draft.observation.time_basis === 'recorded_time' &&
    (draft.observation.policy !== 'explicit' || draft.scope.focus !== 'general')
  )
    return 'Recorded history needs an exact interval and general research focus.';
  const indicators = draft.monitoring.indicators;
  if (new Set(indicators.map((row) => row.id)).size !== indicators.length)
    return 'monitoring.indicators: Indicator IDs must be unique.';
  const parsed = briefDraftSchema.safeParse(draft);
  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    return issue
      ? `${issue.path.join('.')}: ${issue.message}`
      : 'Review the Research Brief fields.';
  }
  return null;
}

/** The next `req-N` not already in use, so removing and adding rows never duplicates an ID. */
export function nextRequirementId(requirements: readonly { id: string }[]): string {
  return nextUnusedId(requirements, 'req');
}

/** Allocate a free monitoring ID without renumbering existing indicators. */
export function nextIndicatorId(indicators: readonly { id: string }[]): string {
  return nextUnusedId(indicators, 'indicator');
}

function nextUnusedId(rows: readonly { id: string }[], prefix: string): string {
  const taken = new Set(rows.map((row) => row.id));
  let number = rows.length + 1;
  while (taken.has(`${prefix}-${String(number)}`)) number += 1;
  return `${prefix}-${String(number)}`;
}

/** A complete canonical definition, so revisions retain options the editor does not expose. */
export function newBriefDraft(): BriefDraft {
  return {
    title: '',
    team_id: null,
    preset_id: null,
    preset_version: null,
    question: { main: '', requirements: [], exclusions: [] },
    scope: {
      country_isos: [],
      focus: 'general',
      subject: null,
      reviewed_aliases: [],
      conflict_id: null,
      hazard: null,
      categories: [],
      area: null,
      map_origin: null,
      map_view_id: null,
      map_revision_id: null,
      disclose_area_to_provider: false,
      plan_id: null,
      parent_report_id: null,
      parent_version: null,
      origin_report_id: null,
      origin_version: null,
    },
    observation: {
      policy: 'relative',
      since: null,
      until: null,
      lookback_hours: 24,
      time_basis: null,
      forecast_horizon_days: null,
    },
    lens: {
      id: 'general',
      audience: null,
      decision_need: null,
      relevance_instructions: null,
      challenge_conclusions: false,
    },
    collection: {
      languages: ['en'],
      terms: null,
      query_variants: [],
      source_policy: 'all_eligible',
      source_ids: null,
      web_search: false,
      candidate_hypotheses: [],
      planned_tasks: [],
      require_primary: false,
      require_local: false,
      require_opposition: false,
    },
    output: {
      depth: 'quick',
      language: 'en',
      style: 'assessment',
      template_id: 'ask',
      preferred_sections: [],
      chart_preference: 'auto',
      table_preference: 'auto',
      model_profile_id: null,
    },
    limits: {
      policy_id: 'ase-brief-limits-v1',
      max_passes: null,
      max_external_operations: null,
      max_model_calls: null,
      max_output_tokens: null,
      max_collection_seconds: null,
    },
    monitoring: {
      indicators: [],
      review_conditions: [],
      prefer_novelty: null,
      organisation_profile_id: null,
    },
    private_inputs: [],
  };
}

export function draftFromBrief(brief: ResearchBrief): BriefDraft {
  const { identity, ...definition } = brief;
  return structuredClone(
    briefDraftSchema.parse({
      ...definition,
      title: identity.title,
      team_id: identity.team_id,
      preset_id: identity.preset_id,
      preset_version: identity.preset_version,
    }),
  );
}

export function briefCanSubscribe(draft: BriefDraft): string | null {
  if (draft.private_inputs.some((input) => input.kind === 'session'))
    return 'Session files need renewed authority for each run, so they cannot be used for subscriptions. This editor cannot replace private references.';
  if (draft.observation.policy === 'explicit')
    return 'Choose a rolling or template-default period for future updates.';
  return null;
}

export function briefCanRun(draft: BriefDraft, now: Date = new Date()): string | null {
  if (
    draft.private_inputs.some(
      (input) => input.expires_at !== null && Date.parse(input.expires_at) <= now.getTime(),
    )
  )
    return 'A private input has expired. This editor cannot renew attachments. Open Research to upload the file again for separate research; this brief keeps its existing references.';
  return null;
}

/**
 * A new brief scoped by a collection plan: its workspace, name and PIRs become the draft's
 * workspace, title and editable questions. SIR direction and scope stay on the server-side plan.
 */
export function seedDraftFromPlan(draft: BriefDraft, plan: CollectionPlan): BriefDraft {
  const cap = { quick: 3, detailed: 6, advanced: 12 }[draft.output.depth];
  return {
    ...draft,
    title: plan.name.slice(0, 120),
    team_id: plan.team_id,
    question: {
      ...draft.question,
      main: draft.question.main || (plan.pirs[0]?.text ?? plan.name),
      requirements: plan.pirs.slice(0, 12).map((pir, index) => ({
        id: pir.code,
        question: pir.text.slice(0, 500),
        required: index < cap,
        priority: index + 1,
      })),
    },
    scope: { ...draft.scope, plan_id: plan.id },
  };
}
