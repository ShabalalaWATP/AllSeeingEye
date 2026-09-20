import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { RfStudyLibrary } from './RfStudyLibrary';
import { createRfDraft } from '@/lib/map/rfDraft';
import { snapshotRfStudy } from '@/lib/map/rfStudy';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
const snapshot = () =>
  snapshotRfStudy(createRfDraft(), [0, 0], null, { origin: '', receiver: '' }, null);
it('does not restore a late file import after the current account loses authority', async () => {
  useAuthStore.setState({ user: { ...plainUser, role: 'admin' }, status: 'authenticated' });
  let finish!: (text: string) => void;
  const file = new File(['{}'], 'study.json', { type: 'application/json' });
  Object.defineProperty(file, 'text', {
    value: () =>
      new Promise<string>((resolve) => {
        finish = resolve;
      }),
  });
  const restoreStudy = vi.fn();
  render(
    <RfStudyLibrary
      workspace={{ baseline: null, setBaseline: vi.fn(), restoreStudy }}
      draft={createRfDraft()}
      snapshot={snapshot}
    />,
  );
  fireEvent.change(screen.getByLabelText('Import radio study file'), { target: { files: [file] } });
  act(() => useAuthStore.setState({ user: { ...plainUser, role: 'user' } }));
  await act(async () => {
    finish(JSON.stringify(snapshot()));
    await Promise.resolve();
  });
  expect(restoreStudy).not.toHaveBeenCalled();
});
