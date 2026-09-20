import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { RfStudyLibrary } from './RfStudyLibrary';
import { createRfDraft } from '@/lib/map/rfDraft';
import { snapshotRfStudy } from '@/lib/map/rfStudy';
import { useRfStudyLibrary } from './useRfStudyLibrary';
vi.mock('./useRfStudyLibrary', () => ({ useRfStudyLibrary: vi.fn() }));
vi.mock('@/components/ui/WorkspaceField', () => ({
  WorkspaceField: () => <span>Workspace selector</span>,
}));
vi.mock('@/lib/hooks/useWorkspaces', () => ({
  useWorkspaces: () => ({ label: (team: string | null) => (team ? 'Team' : 'Personal') }),
  useWorkspaceSelection: () => ({ teamId: 'team-one', ready: true, select: vi.fn() }),
}));
const snapshot = () =>
  snapshotRfStudy(
    { ...createRfDraft(), propagation: 'free-space' },
    [0, 0],
    [0.1, 0],
    { origin: 'Hill', receiver: 'Valley' },
    null,
  );
function library() {
  return {
    items: [{ id: 'one', title: 'Saved study', revision: 2, teamId: null, snapshot: snapshot() }],
    busy: false,
    hasMore: true,
    message: null as string | null,
    refresh: vi.fn().mockResolvedValue(undefined),
    save: vi.fn().mockResolvedValue(undefined),
    remove: vi.fn().mockResolvedValue(undefined),
    loadMore: vi.fn().mockResolvedValue(undefined),
  };
}
let state = library();
beforeEach(() => {
  state = library();
  vi.mocked(useRfStudyLibrary).mockReturnValue(state);
});
afterEach(() => vi.useRealTimers());
function mount(capture = snapshot, baseline: ReturnType<typeof snapshot> | null = null) {
  const workspace = { baseline, restoreStudy: vi.fn(), setBaseline: vi.fn() };
  const view = render(
    <RfStudyLibrary workspace={workspace} draft={createRfDraft()} snapshot={capture} />,
  );
  fireEvent.click(screen.getByText('Saved studies and comparison'));
  return { workspace, ...view };
}
it('saves to the chosen scope and manages selected revisions without widening access', () => {
  const { workspace } = mount();
  fireEvent.change(screen.getByLabelText('Study name'), { target: { value: ' Current ' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save new study' }));
  expect(state.save).toHaveBeenCalledWith(
    'Current',
    expect.objectContaining({ schemaVersion: 1 }),
    undefined,
    'team-one',
  );
  fireEvent.click(screen.getByRole('button', { name: 'Load saved studies' }));
  fireEvent.click(screen.getByRole('button', { name: 'Load more radio studies' }));
  expect(state.refresh).toHaveBeenCalledOnce();
  expect(state.loadMore).toHaveBeenCalledOnce();
  fireEvent.change(screen.getByLabelText('Saved radio study'), { target: { value: 'one' } });
  fireEvent.click(screen.getByRole('button', { name: 'Reopen' }));
  expect(workspace.restoreStudy).toHaveBeenCalledWith(state.items[0]!.snapshot);
  expect(screen.getByLabelText('Study name')).toHaveValue('Saved study');
  fireEvent.click(screen.getByRole('button', { name: 'Compare against' }));
  expect(workspace.setBaseline).toHaveBeenCalledWith(state.items[0]!.snapshot);
  fireEvent.click(screen.getByRole('button', { name: 'Duplicate' }));
  expect(state.save).toHaveBeenLastCalledWith(
    'Saved study copy',
    state.items[0]!.snapshot,
    undefined,
    'team-one',
  );
  fireEvent.click(screen.getByRole('button', { name: 'Update selected' }));
  expect(state.save).toHaveBeenLastCalledWith(
    'Saved study',
    expect.objectContaining({ schemaVersion: 1 }),
    state.items[0],
  );
  fireEvent.click(screen.getByRole('button', { name: 'Delete selected study' }));
  expect(state.remove).toHaveBeenCalledWith('one');
});
it('sets and clears a frozen comparison baseline', () => {
  const { workspace } = mount(snapshot, snapshot());
  fireEvent.click(screen.getByRole('button', { name: 'Set comparison baseline' }));
  expect(workspace.setBaseline).toHaveBeenCalledWith(expect.objectContaining({ schemaVersion: 1 }));
  fireEvent.click(screen.getByRole('button', { name: 'Clear baseline' }));
  expect(workspace.setBaseline).toHaveBeenLastCalledWith(null);
});
it.each([new Error('Check frequency')])(
  'surfaces invalid draft capture and leaves save untouched',
  (problem) => {
    mount(() => {
      throw problem;
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save new study' }));
    expect(state.save).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent(problem.message);
  },
);
it('shows server conflict messages and disables writes while busy or unnamed', () => {
  state.message = 'Revision conflict: reload the saved study.';
  state.busy = true;
  mount();
  expect(screen.getByRole('alert')).toHaveTextContent('Revision conflict');
  expect(screen.getByRole('button', { name: 'Save new study' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Load more radio studies' })).toBeDisabled();
});
it('exports only the validated snapshot and releases its temporary download URL', () => {
  vi.useFakeTimers();
  const createUrl = vi.fn(() => 'blob:study'),
    revokeUrl = vi.fn();
  Object.assign(URL, { createObjectURL: createUrl, revokeObjectURL: revokeUrl });
  const clicked = vi
    .spyOn(HTMLAnchorElement.prototype, 'click')
    .mockImplementation(() => undefined);
  mount();
  fireEvent.click(screen.getByRole('button', { name: 'Export study JSON' }));
  expect(createUrl).toHaveBeenCalledWith(expect.any(Blob));
  expect(clicked).toHaveBeenCalledOnce();
  expect(clicked.mock.instances[0]).toHaveAttribute('download', 'radio-study.json');
  act(() => {
    vi.advanceTimersByTime(1000);
  });
  expect(revokeUrl).toHaveBeenCalledWith('blob:study');
});
it('imports a valid file, rejects invalid or oversized files, and tolerates cancelling the picker', async () => {
  const { workspace } = mount();
  const input = screen.getByLabelText('Import radio study file');
  const clicked = vi.spyOn(input, 'click');
  fireEvent.click(screen.getByRole('button', { name: 'Import study JSON' }));
  expect(clicked).toHaveBeenCalledOnce();
  fireEvent.change(input, { target: { files: [] } });
  expect(workspace.restoreStudy).not.toHaveBeenCalled();
  const upload = (text: string) => {
    const file = new File([text], 'study.json', { type: 'application/json' });
    Object.defineProperty(file, 'text', { value: () => Promise.resolve(text) });
    fireEvent.change(input, { target: { files: [file] } });
  };
  upload(JSON.stringify(snapshot()));
  await waitFor(() => expect(workspace.restoreStudy).toHaveBeenCalledOnce());
  upload('{bad');
  await waitFor(() =>
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid or unsupported'),
  );
  upload('x'.repeat(128 * 1024 + 1));
  expect(screen.getByRole('alert')).toHaveTextContent('128 KiB');
  expect(workspace.restoreStudy).toHaveBeenCalledOnce();
});
