import { useState } from 'react';
import type { CandidateHypothesis, PlannedQueryTask } from '@/lib/api/researchPlan';

export const taskLines = (text: string) =>
  text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
/** Candidates remain hypotheses. IDs keep task references stable while labels are edited. */
export function usePlannedTasks() {
  const [candidates, setCandidates] = useState<Required<CandidateHypothesis>[]>([]);
  const [tasks, setTasks] = useState<Required<PlannedQueryTask>[]>([]);
  const updateCandidate = (id: string, change: Partial<CandidateHypothesis>) =>
    setCandidates((values) =>
      values.map((value) => (value.id === id ? { ...value, ...change } : value)),
    );
  const updateTask = (id: string, change: Partial<PlannedQueryTask>) =>
    setTasks((values) =>
      values.map((value) => (value.id === id ? { ...value, ...change } : value)),
    );
  const candidateHypotheses = candidates.map((value) => ({
    ...value,
    label: value.label.trim(),
    identifiers: taskLines(value.identifiers.join('\n')),
    registry_identifiers: value.registry_identifiers,
  }));
  const plannedTasks = tasks.map((value) => ({
    ...value,
    terms: taskLines(value.terms.join('\n')),
  }));
  const invalidCandidate = candidateHypotheses.some(
    (value) =>
      !value.label.trim() ||
      value.label.length > 200 ||
      value.identifiers.length + value.registry_identifiers.length > 8 ||
      value.registry_identifiers.some((row) => !row.value.trim() || row.value.length > 300) ||
      value.identifiers.some((text) => !text.trim() || text.length > 300) ||
      value.identifiers.join('').length +
        value.registry_identifiers.map((row) => row.value).join('').length >
        1000,
  );
  const incompleteRegistry = (value: Required<PlannedQueryTask>) =>
    value.route === 'candidate_identifier' &&
    (!value.source_id ||
      !candidates.some(
        (candidate) =>
          candidate.id === value.candidate_id &&
          candidate.registry_identifiers.some((row) => row.id === value.identifier_id),
      ));
  const invalidTask = (value: Required<PlannedQueryTask>) =>
    !value.source_id ||
    incompleteRegistry(value) ||
    (value.route === 'terms' && !value.terms.length) ||
    (value.route === 'candidate_identifier' &&
      (value.purpose !== 'disambiguation' || value.terms.length > 0)) ||
    value.terms.length > 12 ||
    value.terms.some((term) => !term.trim() || term.length > 300) ||
    value.terms.join('').length > 1000 ||
    (value.purpose === 'disambiguation' && !value.candidate_id) ||
    (!!value.candidate_id && !candidates.some((candidate) => candidate.id === value.candidate_id));
  const candidateError =
    'Give each candidate a label and up to eight identifiers, at most 1,000 characters combined.';
  const taskError =
    'Choose a source and exact terms or a compatible registry identifier for each task. Identity checks also need a candidate.';
  const error = invalidCandidate
    ? candidateError
    : plannedTasks.some(invalidTask)
      ? taskError
      : null;
  // A capability preview may omit unfinished identifier choices. Submission remains blocked.
  const previewTasks = plannedTasks.filter((task) => !incompleteRegistry(task));
  const previewError = invalidCandidate
    ? candidateError
    : previewTasks.some(invalidTask)
      ? taskError
      : null;
  return {
    candidates,
    tasks,
    candidateHypotheses,
    plannedTasks,
    error,
    previewTasks,
    previewError,
    updateCandidate,
    updateTask,
    addCandidate: () =>
      setCandidates((values) =>
        values.length >= 8
          ? values
          : [
              ...values,
              { id: crypto.randomUUID(), label: '', identifiers: [], registry_identifiers: [] },
            ],
      ),
    removeCandidate: (id: string) => {
      setCandidates((values) => values.filter((value) => value.id !== id));
      setTasks((values) =>
        values.map((value) =>
          value.candidate_id === id ? { ...value, candidate_id: null, identifier_id: null } : value,
        ),
      );
    },
    addTask: () =>
      setTasks((values) =>
        values.length >= 8
          ? values
          : [
              ...values,
              {
                id: crypto.randomUUID(),
                source_id: '',
                purpose: 'challenge',
                terms: [],
                candidate_id: null,
                route: 'terms',
                identifier_id: null,
              },
            ],
      ),
    removeTask: (id: string) => setTasks((values) => values.filter((value) => value.id !== id)),
  };
}
export type PlannedTasksState = ReturnType<typeof usePlannedTasks>;
