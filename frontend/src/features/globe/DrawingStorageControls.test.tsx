import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
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
    dirty: false,
    pendingLoad: null,
    cancelLoad: vi.fn(),
    confirmLoad: vi.fn(() => Promise.resolve()),
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
it('offers save, discard and cancel decisions, requiring applied sketch geometry for saving', () => {
  const storage = { ...state(), pendingLoad: 'saved', dirty: true };
  const { rerender } = render(<DrawingStorageControls storage={storage} />);
  expect(screen.getByRole('region', { name: 'Unsaved drawing changes' })).toHaveFocus();
  fireEvent.click(screen.getByRole('button', { name: 'Save and open' }));
  expect(storage.confirmLoad).toHaveBeenCalledWith('save', undefined);
  fireEvent.click(screen.getByRole('button', { name: 'Discard and open' }));
  expect(storage.confirmLoad).toHaveBeenCalledWith('discard');
  fireEvent.click(screen.getByRole('button', { name: 'Cancel opening' }));
  expect(storage.cancelLoad).toHaveBeenCalledOnce();
  rerender(<DrawingStorageControls storage={{ ...storage, pendingEdits: true }} />);
  expect(screen.getByRole('button', { name: 'Save and open' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Discard and open' })).toBeEnabled();
});
it('offers a team discussion only for a saved, unchanged team collection', () => {
  const team = { ...saved, team_id: '6f1c2c1e-6b1f-4a43-9a43-0b0e7f0c9a11' };
  const { rerender } = render(
    <MemoryRouter>
      <DrawingStorageControls storage={{ ...state(), active: saved }} />
    </MemoryRouter>,
  );
  expect(screen.queryByRole('link', { name: 'Discuss with team' })).not.toBeInTheDocument();
  rerender(
    <MemoryRouter>
      <DrawingStorageControls storage={{ ...state(), active: team }} />
    </MemoryRouter>,
  );
  const link = screen.getByRole('link', { name: 'Discuss with team' });
  const params = new URL(link.getAttribute('href') ?? '', 'http://x').searchParams;
  expect(Object.fromEntries(params)).toEqual({
    team: team.team_id,
    board: 'thread',
    subject: 'drawing_collection',
    subject_id: 'saved',
  });
  // Leaving with unsaved drawings would lose them, so the link waits for a save.
  rerender(
    <MemoryRouter>
      <DrawingStorageControls storage={{ ...state(), active: team, dirty: true }} />
    </MemoryRouter>,
  );
  expect(screen.queryByRole('link', { name: 'Discuss with team' })).not.toBeInTheDocument();
  expect(screen.getByText(/Save the collection before discussing it/)).toBeInTheDocument();
});
