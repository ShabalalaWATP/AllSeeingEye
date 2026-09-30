import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import * as conversations from '@/lib/api/assistantConversations';
import { EyeSavedChats } from './EyeSavedChats';
import { eyeAnswer } from './assistantFixture';
import { useEyeChat, type EyeChat, type EyeChatTurn } from './useEyeChat';

vi.mock('@/lib/api/assistantConversations');

const summary = {
  id: '901e502c-79d0-4274-a39e-458515121302',
  title: 'Harbour investigation',
  turn_count: 2,
  created_at: '2026-09-11T10:00:00Z',
  updated_at: '2026-09-11T10:00:00Z',
};
const saved = { ...summary, turns: [], snapshot_notice: 'Saved snapshot.' };
const turn: EyeChatTurn = {
  id: 1,
  question: 'What changed at the harbour?',
  scope: 'global',
  report: null,
  timeWindow: 'auto',
  sourceCategories: null,
  receivedAt: null,
  saved: false,
  answer: eyeAnswer,
  status: 'answered',
};

beforeEach(() => {
  vi.mocked(conversations.listAssistantConversations).mockResolvedValue({ items: [summary] });
  vi.mocked(conversations.createAssistantConversation).mockResolvedValue(saved);
  vi.mocked(conversations.updateAssistantConversation).mockResolvedValue(saved);
  vi.mocked(conversations.getAssistantConversation).mockResolvedValue(saved);
  vi.mocked(conversations.deleteAssistantConversation).mockResolvedValue(undefined);
});

function mount(overrides: Partial<EyeChat> = {}) {
  const hook = renderHook(() => useEyeChat());
  const chat = {
    ...hook.result.current,
    turns: [turn],
    markSaved: vi.fn(),
    restoreSaved: vi.fn(),
    ...overrides,
  };
  const onResume = vi.fn();
  return { ...render(<EyeSavedChats chat={chat} onResume={onResume} />), chat, onResume };
}

it('saves only the last eight completed answers and trims the fallback title', async () => {
  mount({
    turns: [
      { ...turn, status: 'failed' },
      { ...turn, answer: null },
      ...Array.from({ length: 10 }, (_, index) => ({
        ...turn,
        id: index + 2,
        question: `Q${index}`,
      })),
    ],
  });
  fireEvent.change(screen.getByLabelText('Save this chat'), { target: { value: '   ' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save chat' }));
  await screen.findByText('Conversation saved.');
  const [payload] = vi.mocked(conversations.createAssistantConversation).mock.calls[0]!;
  expect(payload.title).toBe('Q0');
  expect(payload.turns).toHaveLength(8);
  expect(payload.turns[0]?.question).toBe('Q2');
  expect(payload.turns.every((item) => item.report === null)).toBe(true);
});

it('uses the existing saved title and keeps busy or unanswered chats disabled', () => {
  const view = mount({ savedConversationTitle: 'Existing chat', busy: true });
  expect(screen.getByLabelText('Save this chat')).toHaveValue('Existing chat');
  expect(screen.getByRole('button', { name: 'Save chat' })).toBeDisabled();
  view.rerender(
    <EyeSavedChats chat={{ ...view.chat, busy: false, turns: [] }} onResume={view.onResume} />,
  );
  expect(screen.getByRole('button', { name: 'Save chat' })).toBeDisabled();
  expect(conversations.createAssistantConversation).not.toHaveBeenCalled();
});

it('cancels a deletion and only clears the current saved identity when it is deleted', async () => {
  const { chat } = mount({ savedConversationId: summary.id });
  await screen.findByText('Harbour investigation');
  fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(conversations.deleteAssistantConversation).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
  fireEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));
  await screen.findByText('Saved conversation deleted.');
  expect(chat.markSaved).toHaveBeenCalledWith(null, '');
});

it('resumes only after confirming replacement of an existing chat', async () => {
  const { chat, onResume } = mount();
  await screen.findByText('Harbour investigation');
  fireEvent.click(screen.getByRole('button', { name: 'Resume' }));
  expect(conversations.getAssistantConversation).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Confirm resume' }));
  await waitFor(() => expect(onResume).toHaveBeenCalledOnce());
  expect(chat.restoreSaved).toHaveBeenCalledWith(
    saved.id,
    saved.title,
    saved.turns,
    saved.snapshot_notice,
  );
});

const actions = {
  list: conversations.listAssistantConversations,
  save: conversations.createAssistantConversation,
  resume: conversations.getAssistantConversation,
  delete: conversations.deleteAssistantConversation,
};
type Action = keyof typeof actions;

async function start(action: Action) {
  if (action === 'list') return;
  await screen.findByText('Harbour investigation');
  if (action === 'save') fireEvent.click(screen.getByRole('button', { name: 'Save chat' }));
  if (action === 'resume') {
    fireEvent.click(screen.getByRole('button', { name: 'Resume' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm resume' }));
  }
  if (action === 'delete') {
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));
  }
}

it.each(Object.keys(actions) as Action[])(
  'shows a recoverable error when %s fails',
  async (action) => {
    vi.mocked(actions[action]).mockRejectedValueOnce(new Error('Unavailable'));
    const { chat, onResume } = mount();
    await start(action);
    expect(await screen.findByRole('alert')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Save chat' })).toBeEnabled();
    expect(chat.markSaved).not.toHaveBeenCalled();
    expect(onResume).not.toHaveBeenCalled();
  },
);

it.each(
  (Object.keys(actions) as Action[]).flatMap((action) => [
    { action, reject: false },
    { action, reject: true },
  ]),
)(
  'aborts $action on unmount and ignores its late result (reject: $reject)',
  async ({ action, reject }) => {
    let resolve!: (value: never) => void;
    let fail!: (reason: Error) => void;
    const pending = new Promise<never>((done, failed) => {
      resolve = done;
      fail = failed;
    });
    vi.mocked(actions[action]).mockReturnValueOnce(pending);
    const { unmount, chat, onResume } = mount();
    await start(action);
    const calls = vi.mocked(actions[action]).mock.calls;
    const signal = calls[calls.length - 1]?.at(-1) as AbortSignal;
    expect(signal.aborted).toBe(false);
    unmount();
    expect(signal.aborted).toBe(true);
    await act(async () => {
      if (reject) fail(new Error('Late failure'));
      else resolve((action === 'list' ? { items: [summary] } : saved) as never);
      await pending.catch(() => undefined);
    });
    expect(chat.markSaved).not.toHaveBeenCalled();
    expect(chat.restoreSaved).not.toHaveBeenCalled();
    expect(onResume).not.toHaveBeenCalled();
  },
);
