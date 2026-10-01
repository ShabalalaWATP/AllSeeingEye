import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';

import type { EvaluationCatalogue } from '@/lib/api/evaluations';
import { llmProfiles } from '@/test/fixtures';

import { EvaluationStartForm } from './EvaluationStartForm';

const catalogue: EvaluationCatalogue = {
  cases: [
    { id: 'dates', casebook: 'core', title: 'Date ambiguity', fingerprint: 'a'.repeat(64) },
    { id: 'conflict', casebook: 'core', title: 'Conflicting reports', fingerprint: 'b'.repeat(64) },
    {
      id: 'language',
      casebook: 'regional',
      title: 'Language context',
      fingerprint: 'c'.repeat(64),
    },
  ],
  calls_per_case: 4,
  max_calls: 200,
  max_cases: 40,
  estimate_notice: 'Expected usage is an estimate.',
  result_notice: 'Structural checks, not accuracy.',
};
const profiles = [
  llmProfiles[0]!,
  { ...llmProfiles[0]!, id: 'second-profile', name: 'Second connection' },
];

it('updates the estimate when individual or grouped cases are deselected', async () => {
  const user = userEvent.setup();
  render(
    <EvaluationStartForm
      catalogue={catalogue}
      profiles={profiles}
      busy={false}
      running={false}
      onStart={vi.fn()}
    />,
  );
  const allCore = screen.getByRole('checkbox', { name: 'Select every core case' });
  const dates = screen.getByRole('checkbox', { name: /Date ambiguity/ });
  const conflicts = screen.getByRole('checkbox', { name: /Conflicting reports/ });
  const cap = screen.getByRole('textbox', { name: 'Call cap' });
  await user.click(allCore);
  expect(cap).toHaveValue('8');
  await user.click(dates);
  expect(allCore).not.toBeChecked();
  expect(conflicts).toBeChecked();
  expect(cap).toHaveValue('4');
  expect(screen.getByText(/1 case × 4 calls = 4 calls/)).toBeInTheDocument();
  await user.click(allCore);
  expect(dates).toBeChecked();
  await user.click(allCore);
  expect(dates).not.toBeChecked();
  expect(conflicts).not.toBeChecked();
  expect(cap).toHaveValue('1');
  expect(screen.getByRole('button', { name: 'Start evaluation' })).toBeDisabled();
});

it('retains the chosen connection, cases and cap after refusal, then resets a successful selection', async () => {
  const user = userEvent.setup();
  const start = vi.fn().mockResolvedValueOnce(false).mockResolvedValue(true);
  render(
    <EvaluationStartForm
      catalogue={catalogue}
      profiles={profiles}
      busy={false}
      running={false}
      onStart={start}
    />,
  );
  const connection = screen.getByRole('combobox', { name: 'AI connection' });
  await user.selectOptions(connection, profiles[1]!.id);
  const dates = screen.getByRole('checkbox', { name: /Date ambiguity/ });
  const regional = screen.getByRole('checkbox', { name: /Language context/ });
  await user.click(regional);
  await user.click(dates);
  const cap = screen.getByRole('textbox', { name: 'Call cap' });
  await user.clear(cap);
  await user.type(cap, '6');
  const submit = screen.getByRole('button', { name: 'Start evaluation' });
  await user.click(submit);
  expect(start).toHaveBeenCalledExactlyOnceWith({
    profile_id: profiles[1]!.id,
    case_ids: ['dates', 'language'],
    max_calls: 6,
  });
  expect(dates).toBeChecked();
  expect(regional).toBeChecked();
  expect(cap).toHaveValue('6');
  await user.click(submit);
  expect(start).toHaveBeenCalledTimes(2);
  expect(dates).not.toBeChecked();
  expect(regional).not.toBeChecked();
  expect(cap).toHaveValue('1');
  expect(connection).toHaveValue(profiles[1]!.id);
  expect(submit).toBeDisabled();
  await user.click(dates);
  expect(cap).toHaveValue('4');
});

it('keeps the selection stable and prevents another start while an action is pending', async () => {
  const user = userEvent.setup();
  const start = vi.fn();
  const props = { catalogue, profiles, busy: false, running: false, onStart: start };
  const { rerender } = render(<EvaluationStartForm {...props} />);
  const dates = screen.getByRole('checkbox', { name: /Date ambiguity/ });
  await user.click(dates);
  rerender(<EvaluationStartForm {...props} busy />);
  expect(dates).toBeDisabled();
  expect(screen.getByRole('combobox', { name: 'AI connection' })).toBeDisabled();
  expect(screen.getByRole('textbox', { name: 'Call cap' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Start evaluation' }));
  await user.click(dates);
  expect(start).not.toHaveBeenCalled();
  expect(dates).toBeChecked();
  rerender(<EvaluationStartForm {...props} />);
  expect(dates).toBeEnabled();
  expect(screen.getByRole('textbox', { name: 'Call cap' })).toHaveValue('4');
});

it('does not select cases or enable a run when the displayed casebook is empty', async () => {
  const user = userEvent.setup();
  const start = vi.fn();
  render(
    <EvaluationStartForm
      catalogue={{ ...catalogue, cases: [] }}
      profiles={profiles}
      busy={false}
      running={false}
      onStart={start}
    />,
  );
  const allCore = screen.getByRole('checkbox', { name: 'Select every core case' });
  await user.click(allCore);
  expect(allCore).not.toBeChecked();
  expect(screen.getByText(/0 cases × 4 calls = 0 calls/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Start evaluation' })).toBeDisabled();
  expect(start).not.toHaveBeenCalled();
});
