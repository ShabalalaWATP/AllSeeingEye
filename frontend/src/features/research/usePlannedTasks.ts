import { useState } from 'react';
import type { CandidateHypothesis, PlannedQueryTask } from '@/lib/api/researchPlan';

export const taskLines = (text: string) =>
  text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
/** Candidates remain hypotheses. IDs keep task references stable while labels are edited. */
export function usePlannedTasks() {
  const [candidates, setCandidates] = useState<CandidateHypothesis[]>([]);
  const [tasks, setTasks] = useState<PlannedQueryTask[]>([]);
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
  }));
  const plannedTasks = tasks.map((value) => ({
    ...value,
    terms: taskLines(value.terms.join('\n')),
  }));
  const error = candidateHypotheses.some(
    (value) =>
      !value.label.trim() ||
      value.label.length > 200 ||
      value.identifiers.length > 8 ||
      value.identifiers.some((text) => !text.trim() || text.length > 300) ||
      value.identifiers.join('').length > 1000,
  )
    ? 'Give each candidate a label and up to eight identifiers, at most 1,000 characters combined.'
    : plannedTasks.some(
          (value) =>
            !value.source_id ||
            !value.terms.length ||
            value.terms.length > 12 ||
            value.terms.some((term) => !term.trim() || term.length > 300) ||
            value.terms.join('').length > 1000 ||
            (value.purpose === 'disambiguation' && !value.candidate_id) ||
            (value.candidate_id &&
              !candidates.some((candidate) => candidate.id === value.candidate_id)),
        )
      ? 'Choose a source and up to 12 exact terms for each task. Identity checks also need a candidate.'
      : null;
  return {
    candidates,
    tasks,
    candidateHypotheses,
    plannedTasks,
    error,
    updateCandidate,
    updateTask,
    addCandidate: () =>
      setCandidates((values) =>
        values.length >= 8
          ? values
          : [...values, { id: crypto.randomUUID(), label: '', identifiers: [] }],
      ),
    removeCandidate: (id: string) => {
      setCandidates((values) => values.filter((value) => value.id !== id));
      setTasks((values) =>
        values.map((value) =>
          value.candidate_id === id ? { ...value, candidate_id: null } : value,
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
              },
            ],
      ),
    removeTask: (id: string) => setTasks((values) => values.filter((value) => value.id !== id)),
  };
}
export type PlannedTasksState = ReturnType<typeof usePlannedTasks>;
