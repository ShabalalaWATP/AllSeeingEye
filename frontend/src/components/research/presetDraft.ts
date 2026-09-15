import type { BriefDraft } from '@/lib/api/researchBriefSchema';

/** Applying a starter must preserve the authorised map revision and its disclosure choice. */
export function presetDraft(definition: BriefDraft, draft: BriefDraft): BriefDraft {
  if (!(draft.scope.area ?? draft.scope.map_origin ?? draft.scope.map_view_id)) return definition;
  return {
    ...definition,
    team_id: draft.team_id,
    scope: {
      ...definition.scope,
      country_isos: [],
      area: draft.scope.area,
      map_origin: draft.scope.map_origin,
      map_view_id: draft.scope.map_view_id,
      map_revision_id: draft.scope.map_revision_id,
      disclose_area_to_provider: draft.scope.disclose_area_to_provider,
    },
    question: {
      ...definition.question,
      main: draft.question.main || definition.question.main,
    },
  };
}
