/**
 * Where each rejected research request path belongs on the research form. Report-job
 * requests nest the research under `report`, so a FastAPI path reads `report.question` or
 * `report.countries.0`. Most choices are composite pickers, so their reasons link to the
 * step that holds them; the question sits beside its own field.
 */
import type { FieldSpec } from '@/lib/api/fieldErrors';

const at = (...names: string[]) => names.map((name) => `report.${name}`);

export function researchFieldSpecs(advanced: boolean) {
  const scopeStep = advanced ? 'research-countries' : 'research-quick-scope';
  const periodStep = advanced ? 'research-period' : 'research-quick-scope';
  return {
    question: { label: 'Your question', paths: at('question') },
    focus: {
      label: 'Research focus',
      paths: at('research_focus', 'research_subject'),
      target: 'research-question',
    },
    depth: { label: 'How deep to go', paths: at('research_mode'), target: 'research-depth' },
    place: {
      label: 'Where to look',
      paths: at('countries', 'country', 'regions', 'research_area'),
      target: scopeStep,
    },
    themes: { label: 'Which themes', paths: at('categories'), target: 'research-themes' },
    event: {
      label: 'Conflict or disaster',
      paths: at('conflict', 'hazard'),
      target: 'research-focus',
    },
    sources: {
      label: 'What to read',
      paths: at('research_web_search', 'research_input_id'),
      target: 'research-sources',
    },
    period: {
      label: 'Which period',
      paths: at('window_hours', 'research_since', 'research_until', 'research_time_basis'),
      target: periodStep,
    },
    scope: {
      label: 'Scope and sources',
      paths: at('team_id', 'research_languages', 'research_source_ids', 'research_planned_tasks'),
      target: 'research-scope',
    },
  } satisfies Record<string, FieldSpec>;
}
