import { Button } from '@/components/ui/Button';
import { TextAreaField, TextField } from '@/components/ui/Field';
import { CandidateRegistryEditor } from './CandidateRegistryEditor';
import { RegistryTaskEditor } from './RegistryTaskEditor';
import type { TaskSource } from './RegistryTaskEditor';
import type { PlannedTasksState } from './usePlannedTasks';

export function PlannedTasksEditor({
  value,
  sources,
}: {
  value: PlannedTasksState;
  sources: TaskSource[];
}) {
  return (
    <details className="space-y-3 rounded border border-line p-3">
      <summary className="cursor-pointer text-sm font-medium">
        Identity candidates and challenge searches
      </summary>
      <p className="text-xs text-muted">
        Add your own searches for competing identities or conflicting evidence before collection.
        Eligible public-source runs can also add separate model-proposed tasks. Candidate labels and
        identifiers are hypotheses, not verified matches. Exact task terms are retained without
        automatic translation. These tasks share the normal collection budget; an empty or skipped
        search does not confirm a claim. Task phrases also help rank existing context, including
        when a source search is skipped.
      </p>
      {value.candidates.map((candidate, index) => (
        <fieldset key={candidate.id} className="space-y-2 border-t border-line pt-3">
          <legend className="text-sm">Candidate {index + 1}</legend>
          <TextField
            label={`Candidate ${index + 1} label`}
            value={candidate.label}
            maxLength={200}
            onChange={(event) => value.updateCandidate(candidate.id, { label: event.target.value })}
          />
          <TextAreaField
            label={`Candidate ${index + 1} identifiers`}
            rows={2}
            maxLength={1008}
            value={candidate.identifiers.join('\n')}
            hint="Optional context only, one identifier per line. Add a typed registry identifier below to enable an exact lookup."
            onChange={(event) =>
              value.updateCandidate(candidate.id, { identifiers: event.target.value.split('\n') })
            }
          />
          <CandidateRegistryEditor
            candidate={candidate}
            index={index}
            update={(change) => value.updateCandidate(candidate.id, change)}
          />
          <Button variant="ghost" onClick={() => value.removeCandidate(candidate.id)}>
            Remove candidate {index + 1}
          </Button>
        </fieldset>
      ))}
      <Button
        variant="secondary"
        disabled={value.candidates.length >= 8}
        onClick={value.addCandidate}
      >
        Add identity candidate
      </Button>
      {value.tasks.map((task, index) => (
        <fieldset key={task.id} className="space-y-2 border-t border-line pt-3">
          <legend className="text-sm">Additional search {index + 1}</legend>
          <RegistryTaskEditor
            task={task}
            index={index}
            sources={sources}
            candidates={value.candidates}
            update={(change) => value.updateTask(task.id, change)}
          />
          {task.route !== 'candidate_identifier' && (
            <>
              <label className="block text-sm">
                Search {index + 1} purpose
                <select
                  className="mt-1 block w-full rounded border border-line bg-ground p-2"
                  value={task.purpose}
                  onChange={(event) =>
                    value.updateTask(task.id, {
                      purpose:
                        event.target.value === 'disambiguation' ? 'disambiguation' : 'challenge',
                    })
                  }
                >
                  <option value="challenge">Find conflicting evidence</option>
                  <option value="disambiguation">Distinguish an identity candidate</option>
                </select>
              </label>
              <label className="block text-sm">
                Search {index + 1} source
                <select
                  className="mt-1 block w-full rounded border border-line bg-ground p-2"
                  value={task.source_id}
                  onChange={(event) => value.updateTask(task.id, { source_id: event.target.value })}
                >
                  <option value="">Choose a source from the preview</option>
                  {sources.map((source) => (
                    <option
                      key={source.source_id}
                      value={source.source_id}
                      disabled={!source.selected || !source.planned_terms_supported}
                    >
                      {source.source_name}
                      {!source.selected
                        ? ' (not selected)'
                        : !source.planned_terms_supported
                          ? ' (does not support extra search terms)'
                          : ''}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                Search {index + 1} candidate
                <select
                  className="mt-1 block w-full rounded border border-line bg-ground p-2"
                  value={task.candidate_id ?? ''}
                  onChange={(event) =>
                    value.updateTask(task.id, { candidate_id: event.target.value || null })
                  }
                >
                  <option value="">No candidate, general challenge</option>
                  {value.candidates.map((candidate, position) => (
                    <option key={candidate.id} value={candidate.id}>
                      {candidate.label || `Candidate ${position + 1}`}
                    </option>
                  ))}
                </select>
              </label>
              <TextAreaField
                label={`Search ${index + 1} exact terms`}
                rows={3}
                maxLength={1012}
                value={task.terms.join('\n')}
                hint="One phrase per line. Include the name and distinguishing identifier where useful; searches do not establish identity."
                onChange={(event) =>
                  value.updateTask(task.id, { terms: event.target.value.split('\n') })
                }
              />
            </>
          )}
          <Button variant="ghost" onClick={() => value.removeTask(task.id)}>
            Remove search {index + 1}
          </Button>
        </fieldset>
      ))}
      {!sources.length && (
        <p className="text-xs text-muted">Preview the plan first to load available sources.</p>
      )}
      {!!sources.length &&
        !sources.some((source) => source.selected && source.planned_terms_supported) && (
          <p className="text-xs text-muted">
            No selected source supports additional term searches in this preview.
          </p>
        )}
      <Button
        variant="secondary"
        disabled={
          !sources.some(
            (source) =>
              source.selected &&
              (source.planned_terms_supported || source.registry_options?.length),
          ) || value.tasks.length >= 8
        }
        onClick={value.addTask}
      >
        Add challenge or identity search
      </Button>
    </details>
  );
}
