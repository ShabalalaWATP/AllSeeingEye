/**
 * Turns a rejected Research Brief save into a message that names the failing fields and the
 * editor stage that holds them. The server sends dotted paths such as `scope.country_isos`
 * with a fixed reason and never echoes submitted private content.
 */
import { describeError } from '@/lib/api/errors';
import { mapFieldErrors, type FieldSpec } from '@/lib/api/fieldErrors';

import { briefIssueStep, type BriefStep } from './BriefJourney';

const BRIEF_FIELDS = {
  title: 'Brief title',
  'question.main': 'Main research question',
  'question.requirements': 'Requirements',
  question: 'Question',
  'scope.country_isos': 'Country codes',
  'scope.focus': 'Research focus',
  'scope.subject': 'Research subject',
  scope: 'Scope',
  observation: 'Observation period',
  'collection.planned_tasks': 'Planned tasks',
  collection: 'Collection',
  output: 'Output',
  limits: 'Limits',
  monitoring: 'Monitoring',
  private_inputs: 'Private inputs',
} satisfies Record<string, FieldSpec>;

export function describeBriefRejection(error: unknown): {
  message: string;
  step: BriefStep | null;
} {
  const { entries, matched } = mapFieldErrors(error, BRIEF_FIELDS, () => '');
  if (entries.length === 0) return { message: describeError(error), step: null };
  const reasons = entries.map((entry) => `${entry.label}: ${entry.message}`).join(' ');
  const first = entries.find((entry) => entry.target !== null);
  return {
    message: matched ? `Review these fields: ${reasons}` : `${describeError(error)} ${reasons}`,
    step: first === undefined ? null : briefIssueStep(`${first.key}.`),
  };
}
