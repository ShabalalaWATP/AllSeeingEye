import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { useRfStudyLibrary } from './useRfStudyLibrary';
import { createRfDraft } from '@/lib/map/rfDraft';
import { snapshotRfStudy } from '@/lib/map/rfStudy';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import {
  listMapWorkspaceDocuments,
  createMapWorkspaceDocument,
  updateMapWorkspaceDocument,
  removeMapWorkspaceDocument,
} from '@/lib/api/mapWorkspace';
vi.mock('@/lib/api/mapWorkspace', () => ({
  listMapWorkspaceDocuments: vi.fn(),
  createMapWorkspaceDocument: vi.fn(),
  updateMapWorkspaceDocument: vi.fn(),
  removeMapWorkspaceDocument: vi.fn(),
}));
const payload = snapshotRfStudy(
  createRfDraft(),
  [0, 0],
  null,
  { origin: 'Hill', receiver: '' },
  null,
);
const document = {
  id: 'study',
  title: 'Hill study',
  kind: 'radio' as const,
  payload: payload as unknown as Record<string, unknown>,
  revision: 3,
  created_by: 'owner',
  team_id: null,
  created_at: '2026-09-20T00:00:00Z',
  updated_at: '2026-09-20T00:00:00Z',
};
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(listMapWorkspaceDocuments).mockResolvedValue([document]);
});
it('lists only validated studies and uses expected revision on update', async () => {
  const { result } = renderHook(useRfStudyLibrary);
  await act(async () => result.current.refresh());
  expect(result.current.items[0]?.snapshot).toEqual(payload);
  await act(async () => result.current.save('Changed', payload, result.current.items[0]));
  expect(updateMapWorkspaceDocument).toHaveBeenCalledWith(
    'study',
    expect.objectContaining({ title: 'Changed', expected_revision: 3 }),
    expect.any(AbortSignal),
  );
  await act(async () => result.current.save('Copy', payload));
  expect(createMapWorkspaceDocument).toHaveBeenCalledWith(
    expect.objectContaining({ kind: 'radio', title: 'Copy' }),
    expect.any(AbortSignal),
  );
  await act(async () => result.current.remove('study'));
  expect(removeMapWorkspaceDocument).toHaveBeenCalledWith('study', expect.any(AbortSignal));
});
it('discards a late response after an access change even if transport ignores abort', async () => {
  let finish!: (value: (typeof document)[]) => void;
  vi.mocked(listMapWorkspaceDocuments).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const { result } = renderHook(useRfStudyLibrary);
  let pending!: Promise<void>;
  act(() => {
    pending = result.current.refresh();
  });
  act(() => invalidateWorkspaceAccess());
  await act(async () => {
    finish([document]);
    await pending;
  });
  expect(result.current.items).toEqual([]);
  expect(result.current.busy).toBe(false);
});
it('surfaces unsupported documents and save conflicts without silently overwriting', async () => {
  vi.mocked(listMapWorkspaceDocuments).mockResolvedValue([
    { ...document, payload: { schemaVersion: 999 } },
  ]);
  const { result } = renderHook(useRfStudyLibrary);
  await act(async () => result.current.refresh());
  expect(result.current.items).toEqual([]);
  expect(result.current.message).toMatch(/unsupported/);
  vi.mocked(createMapWorkspaceDocument).mockRejectedValue(new Error('Revision conflict'));
  await act(async () => result.current.save('Title', payload));
  await waitFor(() => expect(result.current.message).toBe('Revision conflict'));
});

it.each(['role', 'is_active', 'status'] as const)(
  'aborts same-account %s changes and discards late private results',
  async (field) => {
    useAuthStore.setState({ status: 'authenticated', user: { ...plainUser, role: 'admin' } });
    let finish!: (value: (typeof document)[]) => void;
    vi.mocked(listMapWorkspaceDocuments).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const { result } = renderHook(useRfStudyLibrary);
    let pending!: Promise<void>;
    act(() => {
      pending = result.current.refresh();
    });
    const signal = vi.mocked(listMapWorkspaceDocuments).mock.calls.at(-1)?.[1];
    act(() => {
      if (field === 'status') useAuthStore.setState({ status: 'anonymous' });
      else
        useAuthStore.setState({
          user: {
            ...plainUser,
            role: field === 'role' ? 'user' : 'admin',
            is_active: field !== 'is_active',
          },
        });
    });
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      finish([document]);
      await pending;
    });
    expect(result.current.items).toEqual([]);
  },
);

it('loads one bounded page at a time using raw page offsets and deduplicates documents', async () => {
  const first = Array.from({ length: 100 }, (_, index) => ({ ...document, id: String(index) }));
  vi.mocked(listMapWorkspaceDocuments)
    .mockResolvedValueOnce(first)
    .mockResolvedValueOnce([
      { ...document, id: '99' },
      { ...document, id: '100' },
    ]);
  const { result } = renderHook(useRfStudyLibrary);
  await act(async () => result.current.refresh());
  expect(result.current.hasMore).toBe(true);
  await act(async () => result.current.loadMore());
  expect(result.current.items).toHaveLength(101);
  expect(result.current.hasMore).toBe(false);
  expect(listMapWorkspaceDocuments).toHaveBeenLastCalledWith('radio', expect.any(AbortSignal), {
    offset: 100,
    limit: 100,
  });
});

it('creates in the selected team and preserves the existing scope on revision updates', async () => {
  const { result } = renderHook(useRfStudyLibrary);
  await act(async () => result.current.save('Team study', payload, undefined, 'team-one'));
  expect(createMapWorkspaceDocument).toHaveBeenLastCalledWith(
    expect.objectContaining({ team_id: 'team-one' }),
    expect.any(AbortSignal),
  );
  await act(async () =>
    result.current.save(
      'Revision',
      payload,
      {
        id: 'existing',
        title: 'Existing',
        revision: 4,
        teamId: 'original-team',
        snapshot: payload,
      },
      'different-team',
    ),
  );
  expect(updateMapWorkspaceDocument).toHaveBeenLastCalledWith(
    'existing',
    expect.not.objectContaining({ team_id: expect.anything() }),
    expect.any(AbortSignal),
  );
});
