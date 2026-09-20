import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { RfSiteEditor } from './RfSiteEditor';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
it('applies explicitly ordered WGS84 DMS coordinates and trims the site name', () => {
  const apply = vi.fn();
  render(<RfSiteEditor kind="origin" position={null} name="" onSet={apply} />);
  fireEvent.change(screen.getByLabelText('Transmitter latitude'), {
    target: { value: '51°30′0″N' },
  });
  fireEvent.change(screen.getByLabelText('Transmitter longitude'), {
    target: { value: '0°7′30″W' },
  });
  fireEvent.change(screen.getByLabelText('Transmitter name'), { target: { value: ' Hill ' } });
  fireEvent.click(screen.getByRole('button', { name: 'Apply transmitter site' }));
  expect(apply).toHaveBeenCalledWith('origin', [-0.125, 51.5], 'Hill');
});
it('retains invalid input for correction without moving the map site', () => {
  const apply = vi.fn();
  render(<RfSiteEditor kind="receiver" position={[0, 51]} name="" onSet={apply} />);
  fireEvent.change(screen.getByLabelText('Receiver latitude'), { target: { value: '95' } });
  fireEvent.click(screen.getByRole('button', { name: 'Apply receiver site' }));
  expect(apply).not.toHaveBeenCalled();
  expect(screen.getByRole('alert')).toHaveTextContent('latitude');
});
it('clears unsubmitted coordinates on a same-account authority downgrade', () => {
  useAuthStore.setState({ user: { ...plainUser, role: 'admin' }, status: 'authenticated' });
  render(<RfSiteEditor kind="origin" position={null} name="" onSet={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('Transmitter latitude'), { target: { value: '51.5' } });
  act(() => useAuthStore.setState({ user: { ...plainUser, role: 'user' } }));
  expect(screen.getByLabelText('Transmitter latitude')).toHaveValue('');
});
