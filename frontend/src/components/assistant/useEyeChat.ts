import { useEffect, useRef, useState } from 'react';
import { askAssistant, type AssistantAnswer, type AssistantRequest } from '@/lib/api/assistant';
import { describeError } from '@/lib/api/errors';
import { readAssistantMapContext } from '@/lib/assistantMapContext';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

export type ChatScope = 'global' | 'viewport' | 'selected';
export interface EyeChatTurn {
  id: number;
  question: string;
  answer: AssistantAnswer | null;
  status: 'pending' | 'answered' | 'stopped' | 'failed';
}
export function assistantAuthority() {
  const state = useAuthStore.getState();
  return `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}:${workspaceRevision()}`;
}

/** Ephemeral questions only, no browser persistence and no model-supplied conversation authority. */
export function useEyeChat() {
  const [question, setQuestion] = useState('');
  const [scope, setScope] = useState<ChatScope>('global');
  const [turns, setTurns] = useState<EyeChatTurn[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const request = useScopedRequest();
  const pending = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  useEffect(
    () => () => {
      sequence.current++;
      pending.current?.abort();
    },
    [],
  );
  const stop = () => {
    sequence.current++;
    pending.current?.abort();
    pending.current = null;
    setBusy(false);
    setTurns((previous) =>
      previous.map((turn) => (turn.status === 'pending' ? { ...turn, status: 'stopped' } : turn)),
    );
  };
  const send = async (text = question) => {
    if (pending.current) return;
    const trimmed = text.trim();
    if (!trimmed || trimmed.length > 2000) {
      setError('Enter a question of up to 2,000 characters.');
      return;
    }
    const map = readAssistantMapContext();
    const body: AssistantRequest = {
      question: trimmed,
      prior_questions: turns
        .filter((turn) => turn.status === 'answered')
        .slice(-4)
        .map((turn) => turn.question),
      scope,
    };
    if (scope === 'viewport') {
      if (!map?.bounds) {
        setError('Open the map and let it load before using the current view.');
        return;
      }
      const [west, south, east, north] = map.bounds;
      body.bbox = { west, south, east, north };
    }
    if (scope === 'selected') {
      if (!map?.selected) {
        setError('Select an event, camera or infrastructure item on the map first.');
        return;
      }
      body.selected = { kind: map.selected.kind, id: map.selected.id };
    }
    const controller = new AbortController();
    pending.current = controller;
    const signal = AbortSignal.any([request(), controller.signal]);
    const key = assistantAuthority();
    const id = ++sequence.current;
    const current = () =>
      !signal.aborted && key === assistantAuthority() && id === sequence.current;
    setError(null);
    setBusy(true);
    setQuestion('');
    setTurns((previous) => [
      ...previous.slice(-7),
      { id, question: trimmed, answer: null, status: 'pending' },
    ]);
    try {
      const answer = await askAssistant(body, signal);
      if (current())
        setTurns((previous) =>
          previous.map((turn) => (turn.id === id ? { ...turn, answer, status: 'answered' } : turn)),
        );
    } catch (caught) {
      if (current()) {
        setError(describeError(caught));
        setQuestion(trimmed);
        setTurns((previous) =>
          previous.map((turn) => (turn.id === id ? { ...turn, status: 'failed' } : turn)),
        );
      }
    } finally {
      if (pending.current === controller) {
        pending.current = null;
        if (key === assistantAuthority() && id === sequence.current) setBusy(false);
      }
    }
  };
  return {
    question,
    setQuestion,
    scope,
    setScope,
    turns,
    busy,
    error,
    send,
    stop,
    clear: () => {
      stop();
      setTurns([]);
      setQuestion('');
      setError(null);
    },
  };
}
export type EyeChat = ReturnType<typeof useEyeChat>;
