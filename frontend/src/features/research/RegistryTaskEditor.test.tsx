import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import type { CandidateHypothesis, PlannedQueryTask } from '@/lib/api/researchPlan';
import { RegistryTaskEditor, type TaskSource } from './RegistryTaskEditor';

const candidates: CandidateHypothesis[] = [
  {
    id: 'a',
    label: 'First candidate',
    identifiers: ['123'],
    registry_identifiers: [{ id: 'gb', namespace: 'gb_company_number', value: '123' }],
  },
  {
    id: 'b',
    label: 'Second candidate',
    registry_identifiers: [{ id: 'sec', namespace: 'sec_cik', value: '123' }],
  },
];
const sources: TaskSource[] = [
  {
    source_id: 'uk',
    source_name: 'Companies House',
    selected: true,
    planned_terms_supported: false,
    registry_options: [
      {
        candidate_id: 'a',
        identifier_id: 'gb',
        namespace: 'gb_company_number',
        original_value: '123',
        subject: 'GB:00000123',
      },
    ],
  },
  {
    source_id: 'sec',
    source_name: 'SEC',
    selected: true,
    planned_terms_supported: false,
    registry_options: [
      {
        candidate_id: 'b',
        identifier_id: 'sec',
        namespace: 'sec_cik',
        original_value: '123',
        subject: 'CIK:0000000123',
      },
    ],
  },
];
const task: PlannedQueryTask = {
  id: 'task',
  source_id: 'uk',
  purpose: 'disambiguation',
  route: 'candidate_identifier',
  terms: [],
  candidate_id: 'a',
  identifier_id: 'gb',
};

it('distinguishes identical numeric text by supplied namespace and candidate, without implicit selection', async () => {
  const update = vi.fn();
  render(
    <RegistryTaskEditor
      task={task}
      index={0}
      candidates={candidates}
      sources={sources}
      update={update}
    />,
  );
  expect(screen.getByText('GB:00000123')).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText('Search 1 registry lookup'), '1');
  expect(update).toHaveBeenLastCalledWith({
    source_id: 'sec',
    candidate_id: 'b',
    identifier_id: 'sec',
    terms: [],
    purpose: 'disambiguation',
  });
  await userEvent.selectOptions(screen.getByLabelText('Search 1 registry lookup'), '');
  expect(update).toHaveBeenLastCalledWith({
    source_id: '',
    candidate_id: null,
    identifier_id: null,
    terms: [],
    purpose: 'disambiguation',
  });
  await userEvent.selectOptions(screen.getByLabelText('Search 1 method'), 'terms');
  expect(update).toHaveBeenLastCalledWith({
    route: 'terms',
    identifier_id: null,
    source_id: '',
    terms: [],
  });
});

it('removes deselected source and stale identifier capabilities instead of reusing a previous lookup', () => {
  const props = { task, index: 0, candidates, sources, update: vi.fn() };
  const view = render(<RegistryTaskEditor {...props} />);
  view.rerender(
    <RegistryTaskEditor
      {...props}
      sources={sources.map((source) => ({ ...source, selected: false }))}
    />,
  );
  expect(screen.getByLabelText('Search 1 registry lookup')).toHaveValue('');
  expect(screen.queryByText('GB:00000123')).not.toBeInTheDocument();
  view.rerender(
    <RegistryTaskEditor
      {...props}
      candidates={candidates.map((candidate) => ({ ...candidate, registry_identifiers: [] }))}
    />,
  );
  expect(screen.getAllByRole('option')).toHaveLength(3);
  expect(props.update).not.toHaveBeenCalled();
});

it('keeps same-source candidates separate when their identifier references share a local ID', async () => {
  const update = vi.fn();
  const warnings = vi.spyOn(console, 'error');
  const first = candidates[0]!;
  const second = { ...first, id: 'second', label: 'Other company' };
  const source = sources[0]!;
  render(
    <RegistryTaskEditor
      task={task}
      index={0}
      candidates={[first, second]}
      sources={[
        {
          ...source,
          registry_options: [
            ...source.registry_options!,
            { ...source.registry_options![0]!, candidate_id: 'second' },
          ],
        },
      ]}
      update={update}
    />,
  );
  await userEvent.selectOptions(screen.getByLabelText('Search 1 registry lookup'), '1');
  expect(update).toHaveBeenLastCalledWith({
    source_id: 'uk',
    candidate_id: 'second',
    identifier_id: 'gb',
    terms: [],
    purpose: 'disambiguation',
  });
  expect(warnings).not.toHaveBeenCalled();
});
