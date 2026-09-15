import { useEffect, useId, useRef, useState } from 'react';
import {
  createAssistantConversation,
  deleteAssistantConversation,
  getAssistantConversation,
  listAssistantConversations,
  updateAssistantConversation,
  type AssistantConversationPayload,
  type AssistantConversationSummary,
} from '@/lib/api/assistantConversations';
import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';
import type { EyeChat } from './useEyeChat';

export function EyeSavedChats({ chat, onResume }: { chat: EyeChat; onResume: () => void }) {
  const [items, setItems] = useState<AssistantConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [title, setTitle] = useState(chat.savedConversationTitle);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [resumeTarget, setResumeTarget] = useState<string | null>(null);
  const titleId = useId();
  const pending = useRef(new Set<AbortController>());
  const makeController = () => {
    const controller = new AbortController();
    pending.current.add(controller);
    return controller;
  };
  useEffect(() => {
    const activeRequests = pending.current;
    const controller = new AbortController();
    activeRequests.add(controller);
    void listAssistantConversations(controller.signal)
      .then((page) => {
        if (!controller.signal.aborted) setItems(page.items);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(describeError(caught));
      })
      .finally(() => {
        pending.current.delete(controller);
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => {
      for (const active of activeRequests) active.abort();
      activeRequests.clear();
    };
  }, []);
  const answered = chat.turns.filter((turn) => turn.status === 'answered' && turn.answer);
  const suggestedTitle = chat.savedConversationTitle.length
    ? chat.savedConversationTitle
    : (answered[0]?.question.slice(0, 96) ?? 'Eye conversation');
  const save = async () => {
    if (!answered.length || working || chat.busy) return;
    const name = (title.trim().length ? title.trim() : suggestedTitle).slice(0, 120);
    const body: AssistantConversationPayload = {
      title: name,
      turns: answered.slice(-8).flatMap((turn) =>
        turn.answer
          ? [
              {
                question: turn.question,
                scope: turn.scope,
                time_window: turn.timeWindow,
                source_categories: turn.sourceCategories,
                report:
                  turn.scope === 'report' && turn.report
                    ? { id: turn.report.id, version: turn.report.version }
                    : null,
                answer: turn.answer,
              },
            ]
          : [],
      ),
    };
    const controller = makeController();
    setWorking(true);
    setError(null);
    setStatus(null);
    try {
      const saved = chat.savedConversationId
        ? await updateAssistantConversation(chat.savedConversationId, body, controller.signal)
        : await createAssistantConversation(body, controller.signal);
      if (controller.signal.aborted) return;
      chat.markSaved(saved.id, saved.title);
      setTitle(saved.title);
      setStatus('Conversation saved.');
      const page = await listAssistantConversations(controller.signal);
      setItems(page.items);
    } catch (caught) {
      if (!controller.signal.aborted) setError(describeError(caught));
    } finally {
      pending.current.delete(controller);
      if (!controller.signal.aborted) setWorking(false);
    }
  };
  const resume = async (id: string) => {
    if (working) return;
    const controller = makeController();
    setWorking(true);
    setError(null);
    try {
      const saved = await getAssistantConversation(id, controller.signal);
      if (controller.signal.aborted) return;
      chat.restoreSaved(saved.id, saved.title, saved.turns, saved.snapshot_notice);
      onResume();
    } catch (caught) {
      if (!controller.signal.aborted) setError(describeError(caught));
    } finally {
      pending.current.delete(controller);
      if (!controller.signal.aborted) setWorking(false);
    }
  };
  const erase = async (id: string) => {
    if (working) return;
    const controller = makeController();
    setWorking(true);
    setError(null);
    try {
      await deleteAssistantConversation(id, controller.signal);
      if (controller.signal.aborted) return;
      setItems((previous) => previous.filter((item) => item.id !== id));
      if (chat.savedConversationId === id) chat.markSaved(null, '');
      setDeleteTarget(null);
      setStatus('Saved conversation deleted.');
    } catch (caught) {
      if (!controller.signal.aborted) setError(describeError(caught));
    } finally {
      pending.current.delete(controller);
      if (!controller.signal.aborted) setWorking(false);
    }
  };
  return (
    <section className="eye-saved-chats" aria-label="Saved Eye conversations">
      <div className="eye-save-current">
        <label htmlFor={titleId}>Save this chat</label>
        {chat.scope === 'report' && (
          <p>Report Q&amp;A is saved with the exact report edition and version.</p>
        )}
        <div>
          <input
            id={titleId}
            type="text"
            maxLength={120}
            value={title}
            placeholder={suggestedTitle}
            onChange={(event) => setTitle(event.target.value)}
            disabled={working}
          />
          <button
            type="button"
            onClick={() => void save()}
            disabled={working || chat.busy || !answered.length}
          >
            {chat.savedConversationId ? 'Update saved chat' : 'Save chat'}
          </button>
        </div>
      </div>
      {error && <p role="alert">{error}</p>}
      {status && <p role="status">{status}</p>}
      {loading && <p>Loading saved conversations…</p>}
      {!loading && items.length === 0 && <p>No saved conversations yet.</p>}
      {!loading && items.length > 0 && (
        <ul>
          {items.map((item) => (
            <li key={item.id}>
              <div>
                <strong>{item.title}</strong>
                <span>
                  {item.turn_count} {item.turn_count === 1 ? 'answer' : 'answers'} · Updated{' '}
                  {formatUtc(item.updated_at)}
                </span>
              </div>
              <div className="eye-saved-actions">
                {resumeTarget === item.id ? (
                  <>
                    <span>Replaces current chat</span>
                    <button type="button" disabled={working} onClick={() => void resume(item.id)}>
                      Confirm resume
                    </button>
                    <button type="button" disabled={working} onClick={() => setResumeTarget(null)}>
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    disabled={working || chat.busy}
                    onClick={() => {
                      if (chat.turns.length) setResumeTarget(item.id);
                      else void resume(item.id);
                    }}
                  >
                    Resume
                  </button>
                )}
                {deleteTarget === item.id ? (
                  <>
                    <button type="button" disabled={working} onClick={() => void erase(item.id)}>
                      Confirm delete
                    </button>
                    <button type="button" disabled={working} onClick={() => setDeleteTarget(null)}>
                      Cancel
                    </button>
                  </>
                ) : (
                  <button type="button" disabled={working} onClick={() => setDeleteTarget(item.id)}>
                    Delete
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
