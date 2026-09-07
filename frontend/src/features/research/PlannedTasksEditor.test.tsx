import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { PlannedTasksEditor } from './PlannedTasksEditor';
import { usePlannedTasks } from './usePlannedTasks';
const sources = [
  {
    source_id: 'excluded',
    source_name: 'Excluded source',
    selected: false,
    planned_terms_supported: true,
  },
  {
    source_id: 'registry',
    source_name: 'Registry inventory',
    selected: true,
    planned_terms_supported: false,
  },
  {
    source_id: 'search',
    source_name: 'Search source',
    selected: true,
    planned_terms_supported: true,
  },
];
function Harness() {
  const value = usePlannedTasks();
  return (
    <>
      <PlannedTasksEditor value={value} sources={sources} />
      <output aria-label="Task inputs">{JSON.stringify(value.plannedTasks)}</output>
    </>
  );
}
it('keeps unsupported sources disabled and allows returning an identity check to a general challenge', async () => {
  render(<Harness />);
  const user = userEvent.setup();
  await user.click(screen.getByText('Identity candidates and challenge searches'));
  await user.click(screen.getByRole('button', { name: 'Add identity candidate' }));
  await user.click(screen.getByRole('button', { name: 'Add challenge or identity search' }));
  expect(screen.getByRole('option', { name: 'Excluded source (not selected)' })).toBeDisabled();
  expect(
    screen.getByRole('option', {
      name: 'Registry inventory (does not support extra search terms)',
    }),
  ).toBeDisabled();
  await user.selectOptions(screen.getByLabelText('Search 1 source'), 'search');
  await user.selectOptions(screen.getByLabelText('Search 1 purpose'), 'disambiguation');
  await user.selectOptions(
    screen.getByLabelText('Search 1 candidate'),
    screen.getByRole('option', { name: 'Candidate 1' }),
  );
  expect(screen.getByLabelText('Task inputs')).toHaveTextContent('disambiguation');
  await user.selectOptions(screen.getByLabelText('Search 1 candidate'), '');
  await user.selectOptions(screen.getByLabelText('Search 1 purpose'), 'challenge');
  expect(screen.getByLabelText('Task inputs')).toHaveTextContent('"candidate_id":null');
  expect(screen.getByLabelText('Task inputs')).toHaveTextContent('"purpose":"challenge"');
  await user.click(screen.getByRole('button', { name: 'Remove search 1' }));
  expect(screen.getByLabelText('Task inputs')).toHaveTextContent('[]');
});
