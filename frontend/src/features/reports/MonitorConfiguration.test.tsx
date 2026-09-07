import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { annotationMonitor } from '@/test/fixtures.monitors';
import { MonitorConfiguration } from './MonitorConfiguration';
it('allows name-only edits without skipping pending corrections', async () => {
  const save = vi.fn();
  render(<MonitorConfiguration monitor={annotationMonitor} busy={false} onSave={save} />);
  expect(
    screen.getByText('Alerts are visible within your personal workspace.'),
  ).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Save monitor configuration' })).toBeDisabled();
  await userEvent.clear(screen.getByLabelText('Monitor name'));
  await userEvent.type(screen.getByLabelText('Monitor name'), 'Updated label');
  await userEvent.click(screen.getByRole('button', { name: 'Save monitor configuration' }));
  expect(save).toHaveBeenCalledWith({
    expected_revision: 1,
    action: 'configure',
    name: 'Updated label',
    categories: ['claim'],
    notify_on_change: false,
    rebaseline: false,
  });
});
it('requires deliberate fresh baseline for policy changes and resets confirmation when policy changes again', async () => {
  const save = vi.fn();
  render(<MonitorConfiguration monitor={annotationMonitor} busy={false} onSave={save} />);
  await userEvent.click(screen.getByLabelText('Create alerts for meaningful changes'));
  expect(screen.getByRole('button', { name: 'Save monitor configuration' })).toBeDisabled();
  await userEvent.click(
    screen.getByLabelText(
      'I confirm a fresh baseline for this notification policy, skipping pending differences.',
    ),
  );
  await userEvent.click(screen.getByRole('button', { name: 'Save monitor configuration' }));
  expect(save).toHaveBeenCalledWith(
    expect.objectContaining({ notify_on_change: true, rebaseline: true }),
  );
  await userEvent.click(screen.getByLabelText('Selected claims'));
  expect(screen.getByRole('button', { name: 'Save monitor configuration' })).toBeDisabled();
  expect(
    screen.getByLabelText(
      'I confirm a fresh baseline for this notification policy, skipping pending differences.',
    ),
  ).not.toBeChecked();
});
it('limits categories to watched roots across all three supported kinds', () => {
  render(
    <MonitorConfiguration
      monitor={{
        ...annotationMonitor,
        team_id: 'team-1',
        selection: {
          ...annotationMonitor.selection,
          identity_revisions: [{ decision_id: 'identity', revision_id: 'ir' }],
          relationship_revisions: [{ relationship_id: 'relationship', revision_id: 'rr' }],
        },
      }}
      busy
      onSave={vi.fn()}
    />,
  );
  expect(
    screen.getByText("Alerts are shared with authorised members of this report's team workspace."),
  ).toBeInTheDocument();
  expect(screen.getByLabelText('Selected identity reviews')).toBeDisabled();
  expect(screen.getByLabelText('Selected organisation relationships')).toBeDisabled();
  expect(screen.queryByLabelText('Confidence')).not.toBeInTheDocument();
});
