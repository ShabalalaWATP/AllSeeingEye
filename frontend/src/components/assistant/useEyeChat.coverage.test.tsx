import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/assistant';
import { registerAssistantMapContext, type AssistantMapContext } from '@/lib/assistantMapContext';
import { eyeAnswer } from './assistantFixture';
import { useEyeChat, type SavedEyeTurn } from './useEyeChat';

beforeEach(() => {
  vi.spyOn(api, 'askAssistant').mockResolvedValue(eyeAnswer);
});
let unregister: (() => void) | undefined;
afterEach(() => {
  unregister?.();
  unregister = undefined;
});
const selectedReport = {
  id: '11111111-1111-4111-8111-111111111111',
  version: 2,
  title: 'Saved report',
  dataCutoff: null,
};
const reportAnswer: api.AssistantAnswer = {
  ...eyeAnswer,
  scope: { ...eyeAnswer.scope, mode: 'report' },
  report: {
    id: selectedReport.id,
    version_id: '22222222-2222-4222-8222-222222222222',
    version: 2,
    title: selectedReport.title,
    data_cutoff: null,
  },
};
const savedTurn: SavedEyeTurn = {
  question: 'Saved question',
  scope: 'global',
  time_window: 'auto',
  answer: eyeAnswer,
};

it.each(['', ' ', 'x'.repeat(2001)])(
  'rejects empty or oversized question without sending',
  async (question) => {
    const { result } = renderHook(useEyeChat);
    await act(async () => result.current.send(question));
    expect(result.current.error).toContain('up to 2,000 characters');
    expect(api.askAssistant).not.toHaveBeenCalled();
    expect(result.current.turns).toEqual([]);
  },
);

it.each([
  ['report', 'Open an exact report version'],
  ['selected', 'Select an event'],
  ['viewport', 'Open the map'],
] as const)('requires an available %s context', async (scope, message) => {
  const { result } = renderHook(useEyeChat);
  act(() => result.current.setScope(scope));
  await act(async () => result.current.send('What changed?'));
  expect(result.current.error).toContain(message);
  expect(api.askAssistant).not.toHaveBeenCalled();
});

it('restores only valid categories, normalises old options and drops invalid report snapshots', () => {
  const { result } = renderHook(useEyeChat);
  act(() =>
    result.current.restoreSaved(
      'chat',
      'Old chat',
      [
        {
          ...savedTurn,
          scope: 'unknown',
          time_window: 'invalid',
          source_categories: ['bad', 'maritime'],
        },
        { ...savedTurn, scope: 'report', report: { id: selectedReport.id, version: 1 } },
      ],
      'Historical snapshot',
    ),
  );
  expect(result.current.turns).toHaveLength(1);
  expect(result.current.turns[0]).toMatchObject({
    scope: 'global',
    timeWindow: 'auto',
    sourceCategories: ['maritime'],
    saved: true,
    receivedAt: null,
    answer: { continuation_id: null, model: null },
  });
  expect(result.current.savedSnapshotNotice).toBe('Historical snapshot');
  act(() => result.current.restoreSaved('empty', 'Nothing valid', [], 'Nothing to restore'));
  expect(result.current).toMatchObject({
    turns: [],
    scope: 'global',
    report: null,
    timeWindow: 'auto',
    sourceCategories: null,
  });
});

it('restores exact report snapshots but refuses mismatched editions or non-report answers', () => {
  const { result } = renderHook(useEyeChat);
  const exact: SavedEyeTurn = {
    ...savedTurn,
    scope: 'report',
    report: { id: selectedReport.id, version: 2 },
    answer: reportAnswer,
    time_window: '48',
    source_categories: ['unknown'],
  };
  act(() =>
    result.current.restoreSaved(
      'report-chat',
      'Report',
      [
        { ...exact, report: { id: 'different', version: 2 } },
        { ...exact, report: { id: selectedReport.id, version: 1 } },
        { ...exact, answer: { ...reportAnswer, scope: eyeAnswer.scope } },
        exact,
      ],
      'Snapshot',
    ),
  );
  expect(result.current.turns).toHaveLength(1);
  expect(result.current.report).toEqual(selectedReport);
  expect(result.current.scope).toBe('report');
  expect(result.current.timeWindow).toBe('48');
  expect(result.current.sourceCategories).toBeNull();
});

it.each(['same', 'changed', 'missing'] as const)(
  'reuses viewport continuation only for the same bounds (%s)',
  async (kind) => {
    let context: AssistantMapContext = { bounds: [1, 2, 3, 4], selected: null };
    unregister = registerAssistantMapContext(() => context);
    vi.mocked(api.askAssistant).mockResolvedValue({
      ...eyeAnswer,
      scope: {
        mode: 'viewport',
        selected: null,
        bbox: kind === 'missing' ? null : { west: 1, south: 2, east: 3, north: 4 },
      },
    });
    const { result } = renderHook(useEyeChat);
    act(() => result.current.setScope('viewport'));
    await act(async () => result.current.send('What is happening here?'));
    if (kind === 'changed') context = { ...context, bounds: [2, 3, 4, 5] };
    await act(async () => result.current.send('Which of those are recent?'));
    const body = vi.mocked(api.askAssistant).mock.calls[1]![0];
    if (kind === 'same') expect(body.continuation_id).toBe(eyeAnswer.continuation_id);
    else expect(body).not.toHaveProperty('continuation_id');
    expect(result.current.turns).toHaveLength(2);
  },
);

it('preserves a new draft when a pending answer fails and retains earlier answered turns', async () => {
  const { result } = renderHook(useEyeChat);
  await act(async () => result.current.send('First question'));
  let reject!: (reason: Error) => void;
  vi.mocked(api.askAssistant).mockReturnValue(
    new Promise((_done, fail) => {
      reject = fail;
    }),
  );
  let request!: Promise<void>;
  act(() => {
    request = result.current.send('Failed question');
  });
  act(() => result.current.setQuestion('Next question draft'));
  await act(async () => {
    reject(new Error('Service unavailable'));
    await request;
  });
  expect(result.current.question).toBe('Next question draft');
  expect(result.current.turns.map((turn) => turn.status)).toEqual(['answered', 'failed']);
  expect(result.current.error).toBeTruthy();
  expect(result.current.busy).toBe(false);
});

it.each([false, true])(
  'uses selected-record continuation only for the same record, changed=%s',
  async (changed) => {
    let selected = { kind: 'event' as const, id: 'event-1', title: 'First record' };
    unregister = registerAssistantMapContext(() => ({ bounds: null, selected }));
    vi.mocked(api.askAssistant).mockResolvedValue({
      ...eyeAnswer,
      scope: { mode: 'selected', bbox: null, selected },
    });
    const { result } = renderHook(useEyeChat);
    act(() => result.current.setScope('selected'));
    await act(async () => result.current.send('Explain the selected event'));
    if (changed) selected = { ...selected, id: 'event-2' };
    await act(async () => result.current.send('What about those sources?'));
    const body = vi.mocked(api.askAssistant).mock.calls[1]![0];
    expect(body.selected?.id).toBe(changed ? 'event-2' : 'event-1');
    if (changed) expect(body).not.toHaveProperty('continuation_id');
    else expect(body.continuation_id).toBe(eyeAnswer.continuation_id);
  },
);

it('rejects an answer bound to another report edition without adding its private content', async () => {
  vi.mocked(api.askAssistant).mockResolvedValue({
    ...reportAnswer,
    report: { ...reportAnswer.report!, version: 3 },
  });
  const { result } = renderHook(useEyeChat);
  act(() => result.current.beginReport(selectedReport));
  await act(async () => result.current.send('Explain this edition'));
  expect(result.current.error).toContain('did not match the selected report edition');
  expect(result.current.turns[0]).toMatchObject({ status: 'failed', answer: null });
  expect(result.current.question).toBe('Explain this edition');
});

it.each([false, true])(
  'aborts on unmount and ignores late completion, failed=%s',
  async (failed) => {
    let resolve!: (answer: api.AssistantAnswer) => void;
    let reject!: (reason: Error) => void;
    vi.mocked(api.askAssistant).mockReturnValue(
      new Promise((done, fail) => {
        resolve = done;
        reject = fail;
      }),
    );
    const { result, unmount } = renderHook(useEyeChat);
    let request!: Promise<void>;
    act(() => {
      request = result.current.send('Private question');
    });
    const signal = vi.mocked(api.askAssistant).mock.calls[0]![1];
    unmount();
    expect(signal.aborted).toBe(true);
    await act(async () => {
      if (failed) reject(new Error('Late failure'));
      else resolve(eyeAnswer);
      await request;
    });
    expect(result.current.turns[0]?.answer).toBeNull();
    expect(result.current.error).toBeNull();
  },
);
