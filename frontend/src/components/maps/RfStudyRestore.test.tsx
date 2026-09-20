import { useState } from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { RfCalculatorPanel } from './RfCalculatorPanel';
import { createRfDraft } from '@/lib/map/rfDraft';
import { snapshotRfStudy } from '@/lib/map/rfStudy';
import type { RfStudyWorkspace } from './RfStudyLibrary';
const { analyse } = vi.hoisted(() => ({
  analyse: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
}));
vi.mock('./useRfAnalysis', () => ({
  useRfAnalysis: () => ({
    analyse,
    cancel: () => undefined,
    busy: false,
    error: null,
    progress: null,
  }),
}));
vi.mock('./RfStudyLibrary', () => ({
  RfStudyLibrary: ({ workspace }: { workspace: RfStudyWorkspace }) => (
    <button
      onClick={() =>
        workspace.restoreStudy(
          snapshotRfStudy(
            { ...createRfDraft(), values: { ...createRfDraft().values, frequencyMHz: '450' } },
            [0, 0],
            [0.1, 0],
            { origin: '', receiver: '' },
            null,
          ),
        )
      }
    >
      Reopen test study
    </button>
  ),
}));
function Harness() {
  const [draft, setDraft] = useState(createRfDraft);
  return (
    <RfCalculatorPanel
      origin={[0, 0]}
      receiver={[0.1, 0]}
      draft={draft}
      onDraftChange={setDraft}
      studyWorkspace={{
        baseline: null,
        setBaseline: () => undefined,
        restoreStudy: (value) => setDraft(value.draft),
      }}
    />
  );
}
afterEach(() => vi.useRealTimers());
it('requires a new explicit analysis after reopening a saved study even when automatic updates were armed', async () => {
  vi.useFakeTimers();
  render(<Harness />);
  fireEvent.click(screen.getByRole('button', { name: 'Analyse terrain' }));
  expect(analyse).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Reopen test study' }));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(60000);
  });
  expect(screen.getByLabelText('Frequency (MHz)')).toHaveValue(450);
  expect(analyse).toHaveBeenCalledTimes(1);
});
