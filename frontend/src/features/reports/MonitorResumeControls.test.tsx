import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { MonitorResumeControls } from './MonitorResumeControls';
it('keeps catch-up separate from explicitly skipping pending differences', async () => {
  const catchUp = vi.fn();
  const fresh = vi.fn();
  const { rerender } = render(
    <MonitorResumeControls busy={false} onCatchUp={catchUp} onFreshBaseline={fresh} />,
  );
  expect(screen.getByRole('button', { name: 'Confirm fresh baseline and resume' })).toBeDisabled();
  await userEvent.click(screen.getByRole('button', { name: 'Resume and catch up' }));
  expect(catchUp).toHaveBeenCalledOnce();
  expect(fresh).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole('checkbox'));
  await userEvent.click(screen.getByRole('button', { name: 'Confirm fresh baseline and resume' }));
  expect(fresh).toHaveBeenCalledOnce();
  rerender(<MonitorResumeControls busy onCatchUp={catchUp} onFreshBaseline={fresh} />);
  expect(screen.getByRole('button', { name: 'Resume and catch up' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Confirm fresh baseline and resume' })).toBeDisabled();
  expect(screen.getByRole('checkbox')).toBeDisabled();
});
