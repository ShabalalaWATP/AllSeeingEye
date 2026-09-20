import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { DrawingStorageControls } from './DrawingStorageControls';
import type { DrawingWorkspace } from './useDrawingWorkspace';

const scope = vi.hoisted(() => ({ teamId: '', ready: true, select: vi.fn() }));
vi.mock('@/lib/hooks/useWorkspaces', () => ({
  useWorkspaceSelection: () => scope,
  useWorkspaces: () => ({
    teams: [],
    error: null,
    label: (team: string | null) => (team ? 'Team: Test team' : 'Personal'),
  }),
}));
const saved = {
  id: 'saved',
  kind: 'drawings' as const,
  title: 'Coast',
  payload: {},
  revision: 2,
  created_by: 'actor',
  team_id: null,
  created_at: '',
  updated_at: '',
};
function state(): DrawingWorkspace['storage'] {
  return {
    active: null,
    pendingEdits: false,
    documents: [],
    hasMore: false,
    title: 'Drawings',
    setTitle: vi.fn(),
    busy: false,
    error: null,
    notice: null,
    browse: vi.fn(() => Promise.resolve()),
    loadMore: vi.fn(() => Promise.resolve()),
    load: vi.fn(() => Promise.resolve()),
    save: vi.fn(() => Promise.resolve()),
  };
}
it('saves new work to the chosen scope and browses explicit pages', () => {
  scope.teamId = 'team-id';
  const storage = { ...state(), documents: [saved], hasMore: true };
  render(<DrawingStorageControls storage={storage} />);
  fireEvent.change(screen.getByLabelText('Collection title'), { target: { value: 'Survey' } });
  expect(storage.setTitle).toHaveBeenCalledWith('Survey');
  fireEvent.click(screen.getByRole('button', { name: 'Save collection' }));
  expect(storage.save).toHaveBeenCalledWith(false, 'team-id');
  fireEvent.click(screen.getByRole('button', { name: 'Browse saved' }));
  expect(storage.browse).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole('button', { name: 'Open Coast (revision 2)' }));
  expect(storage.load).toHaveBeenCalledWith('saved');
  fireEvent.click(screen.getByRole('button', { name: 'Load more collections' }));
  expect(storage.loadMore).toHaveBeenCalledOnce();
  scope.teamId = '';
});
it('keeps the active collection scope visible and makes copies personal', () => {
  scope.teamId = '';
  const storage = { ...state(), active: saved, notice: 'Saved revision 2.' };
  const { rerender } = render(<DrawingStorageControls storage={storage} />);
  expect(screen.getByText(/Saved in Personal/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Save collection' }));
  expect(storage.save).toHaveBeenCalledWith(false, undefined);
  fireEvent.click(screen.getByRole('button', { name: 'Save a personal copy' }));
  expect(storage.save).toHaveBeenCalledWith(true);
  expect(screen.getByRole('status')).toHaveTextContent('Saved revision 2');
  rerender(
    <DrawingStorageControls
      storage={{
        ...storage,
        pendingEdits: true,
        notice: null,
        error: 'Resolve this revision conflict.',
      }}
    />,
  );
  expect(screen.getByRole('button', { name: 'Save collection' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Save a personal copy' })).toBeDisabled();
  expect(screen.getByRole('status')).toHaveTextContent('apply its edits');
  expect(screen.getByRole('alert')).toHaveTextContent('revision conflict');
});
