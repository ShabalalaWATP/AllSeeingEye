import type { CandidateHypothesis, PlannedQueryTask, ResearchPlan } from '@/lib/api/researchPlan';
import { registryLabels } from '@/lib/api/registryRouting';
import { RegistryLookupDetails } from '@/components/reports/RegistryLookupDetails';

export type TaskSource = Pick<
  ResearchPlan['tasks'][number],
  'source_id' | 'source_name' | 'selected' | 'planned_terms_supported' | 'registry_options'
> &
  Partial<Pick<ResearchPlan['tasks'][number], 'temporal_scope'>>;

export function RegistryTaskEditor({
  task,
  index,
  sources,
  candidates,
  update,
}: {
  task: PlannedQueryTask;
  index: number;
  sources: TaskSource[];
  candidates: CandidateHypothesis[];
  update: (change: Partial<PlannedQueryTask>) => void;
}) {
  const choices = sources
    .filter((source) => source.selected)
    .flatMap((source) =>
      (source.registry_options ?? []).flatMap((option) => {
        const candidate = candidates.find((row) => row.id === option.candidate_id);
        const identifier = candidate?.registry_identifiers?.find(
          (row) => row.id === option.identifier_id,
        );
        return identifier?.namespace === option.namespace &&
          identifier.value === option.original_value
          ? [{ source, option, label: candidate?.label ?? option.candidate_id }]
          : [];
      }),
    );
  const selected = choices.find(
    (choice) =>
      choice.source.source_id === task.source_id &&
      choice.option.candidate_id === task.candidate_id &&
      choice.option.identifier_id === task.identifier_id,
  );
  return (
    <div className="space-y-3">
      <label className="block text-sm">
        Search {index + 1} method
        <select
          className="mt-1 block w-full rounded border border-line bg-ground p-2"
          value={task.route}
          onChange={(event) =>
            update(
              event.target.value === 'candidate_identifier'
                ? {
                    route: 'candidate_identifier',
                    purpose: 'disambiguation',
                    terms: [],
                    source_id: '',
                    candidate_id: null,
                    identifier_id: null,
                  }
                : { route: 'terms', identifier_id: null, source_id: '', terms: [] },
            )
          }
        >
          <option value="terms">Search exact phrases</option>
          <option value="candidate_identifier">Look up an exact registry identifier</option>
        </select>
      </label>
      {task.route === 'candidate_identifier' && (
        <>
          <label className="block text-sm">
            Search {index + 1} registry lookup
            <select
              className="mt-1 block w-full rounded border border-line bg-ground p-2"
              value={selected ? String(choices.indexOf(selected)) : ''}
              onChange={(event) => {
                const choice =
                  event.target.value === '' ? undefined : choices[Number(event.target.value)];
                update({
                  source_id: choice?.source.source_id ?? '',
                  candidate_id: choice?.option.candidate_id ?? null,
                  identifier_id: choice?.option.identifier_id ?? null,
                  terms: [],
                  purpose: 'disambiguation',
                });
              }}
            >
              <option value="">Choose a compatible identifier and source</option>
              {choices.map((choice, position) => (
                <option
                  key={`${choice.source.source_id}:${choice.option.candidate_id}:${choice.option.identifier_id}`}
                  value={position}
                >
                  {choice.source.source_name} · {choice.label} ·{' '}
                  {registryLabels[choice.option.namespace]}: {choice.option.original_value}
                </option>
              ))}
            </select>
          </label>
          {selected ? (
            <>
              <RegistryLookupDetails value={selected.option} candidateLabel={selected.label} />
              <p className="text-xs text-muted">{selected.source.temporal_scope}</p>
            </>
          ) : (
            <p role="status" className="text-xs text-amber">
              Preview with your typed identifiers and selected sources to load compatible lookups.
              Provider availability, company focus, country and date restrictions still apply.
              Changing a candidate or scope requires another preview before choosing a lookup.
              Incomplete identifier tasks are omitted from previews; finish each choice before
              starting research.
            </p>
          )}
        </>
      )}
    </div>
  );
}
