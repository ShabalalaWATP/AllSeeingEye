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
  const parsed = briefDraftSchema.safeParse(draft);
  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    return issue
      ? `${issue.path.join('.')}: ${issue.message}`
      : 'Review the Research Brief fields.';
  }
  return null;
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
    return 'Session files need renewed authority. Remove them or use a durable report input.';
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
    return 'A private input has expired. Renew the input before starting research.';
  return null;
}
