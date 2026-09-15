import { useEffect, useRef, useState } from 'react';
import {
  askAssistant,
  assistantSourceCategorySchema,
  type AssistantAnswer,
  type AssistantRequest,
} from '@/lib/api/assistant';
import { ApiError, describeError } from '@/lib/api/errors';
import { readAssistantMapContext } from '@/lib/assistantMapContext';
import type { AssistantReportSelection } from '@/lib/assistantReportContext';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import type { EyeSourceCategory } from './EyeSourceFilter';

export type ChatScope = 'global' | 'viewport' | 'selected' | 'report';
export type ChatTimeWindow = 'auto' | '48' | '120' | '168' | '336' | '720' | '2160' | '8760';
export interface EyeChatTurn {
  id: number;
  question: string;
  scope: ChatScope;
  report: AssistantReportSelection | null;
  timeWindow: ChatTimeWindow;
  sourceCategories: EyeSourceCategory[] | null;
  receivedAt: number | null;
  saved: boolean;
  answer: AssistantAnswer | null;
  status: 'pending' | 'answered' | 'stopped' | 'failed';
}
export function assistantAuthority() {
  const state = useAuthStore.getState();
  return `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}:${workspaceRevision()}`;
}

/** Do not spend an expiring server-side evidence token on an unrelated question. */
export function refersToPriorAnswer(text: string): boolean {
  return /\b(those|these|them|earlier|previous|above|that answer|your answer|same (sources|records|events|reports)|what about|which of (them|those|these))\b/i.test(
    text,
  );
}
export function continuationFresh(receivedAt: number | null, now = Date.now()): boolean {
  return receivedAt !== null && now >= receivedAt && now - receivedAt < 18 * 60_000;
}
export interface SavedEyeTurn {
  question: string;
  scope: string;
  time_window: string;
  source_categories?: string[] | null;
  report?: { id: string; version: number } | null;
  answer: AssistantAnswer;
}
function savedScope(value: string): ChatScope {
  return value === 'viewport' || value === 'selected' || value === 'report' ? value : 'global';
}
function savedTimeWindow(value: string): ChatTimeWindow {
  return ['48', '120', '168', '336', '720', '2160', '8760'].includes(value)
    ? (value as ChatTimeWindow)
    : 'auto';
}
function savedCategories(values: string[] | null): EyeSourceCategory[] | null {
  const safe = values?.flatMap((value) => {
    const parsed = assistantSourceCategorySchema.safeParse(value);
    return parsed.success ? [parsed.data] : [];
  });
  return safe?.length ? safe : null;
}
function savedReport(turn: SavedEyeTurn): AssistantReportSelection | null {
  const answerReport = turn.answer.report;
  if (
    turn.scope !== 'report' ||
    !turn.report ||
    turn.report.id !== answerReport?.id ||
    turn.report.version !== answerReport.version ||
    turn.answer.scope.mode !== 'report'
  )
    return null;
  return {
    id: turn.report.id,
    version: turn.report.version,
    title: answerReport.title,
    dataCutoff: answerReport.data_cutoff,
  };
}

/** Ephemeral questions only, no browser persistence and no model-supplied conversation authority. */
export function useEyeChat() {
  const [question, setQuestion] = useState('');
  const [scope, setScope] = useState<ChatScope>('global');
  const [report, setReport] = useState<AssistantReportSelection | null>(null);
  const [timeWindow, setTimeWindow] = useState<ChatTimeWindow>('auto');
  const [sourceCategories, setSourceCategories] = useState<EyeSourceCategory[] | null>(null);
  const [turns, setTurns] = useState<EyeChatTurn[]>([]);
  const [savedConversationId, setSavedConversationId] = useState<string | null>(null);
  const [savedConversationTitle, setSavedConversationTitle] = useState('');
  const [savedSnapshotNotice, setSavedSnapshotNotice] = useState<string | null>(null);
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
    const map = scope === 'report' ? null : readAssistantMapContext();
    if (scope === 'report' && !report) {
      setError('Open an exact report version before asking about it.');
      return;
    }
    const body: AssistantRequest = {
      question: trimmed,
      prior_questions: turns
        .filter(
          (turn) =>
            turn.status === 'answered' &&
            (scope !== 'report' ||
              (turn.scope === 'report' &&
                turn.report?.id === report?.id &&
                turn.report?.version === report?.version)),
        )
        .slice(-4)
        .map((turn) => turn.question),
      scope,
    };
    if (scope === 'report' && report) body.report = { id: report.id, version: report.version };
    if (scope !== 'report' && sourceCategories?.length) body.source_categories = sourceCategories;
    if (scope !== 'report' && timeWindow !== 'auto') {
      const until = new Date();
      body.time_range = {
        since: new Date(until.getTime() - Number(timeWindow) * 3_600_000).toISOString(),
        until: until.toISOString(),
      };
    }
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
    const previous = [...turns].reverse().find((turn) => turn.status === 'answered');
    if (
      scope !== 'report' &&
      refersToPriorAnswer(trimmed) &&
      previous?.answer?.continuation_id &&
      continuationFresh(previous.receivedAt) &&
      previous.scope === scope &&
      previous.timeWindow === timeWindow &&
      JSON.stringify(previous.sourceCategories) === JSON.stringify(sourceCategories) &&
      (scope !== 'selected' || previous.answer.scope.selected?.id === body.selected?.id) &&
      (scope !== 'viewport' ||
        (previous.answer.scope.bbox &&
          JSON.stringify(previous.answer.scope.bbox) === JSON.stringify(body.bbox)))
    )
      body.continuation_id = previous.answer.continuation_id;
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
      {
        id,
        question: trimmed,
        scope,
        report: scope === 'report' ? report : null,
        timeWindow,
        sourceCategories,
        receivedAt: null,
        saved: false,
        answer: null,
        status: 'pending',
      },
    ]);
    try {
      const answer = await askAssistant(body, signal);
      if (
        scope === 'report' &&
        (answer.scope.mode !== 'report' ||
          !answer.report ||
          answer.report.id !== report?.id ||
          answer.report.version !== report.version)
      )
        throw new ApiError(
          502,
          'report_context_mismatch',
          'The answer did not match the selected report edition. No answer was added.',
        );
      if (current())
        setTurns((previous) =>
          previous.map((turn) =>
            turn.id === id ? { ...turn, answer, receivedAt: Date.now(), status: 'answered' } : turn,
          ),
        );
    } catch (caught) {
      if (current()) {
        setError(describeError(caught));
        setQuestion((draft) => (draft.trim() ? draft : trimmed));
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
    report,
    beginReport: (selection: AssistantReportSelection) => {
      stop();
      setTurns([]);
      setQuestion('');
      setError(null);
      setScope('report');
      setReport(selection);
      setTimeWindow('auto');
      setSourceCategories(null);
      setSavedConversationId(null);
      setSavedConversationTitle('');
      setSavedSnapshotNotice(null);
    },
    timeWindow,
    setTimeWindow,
    sourceCategories,
    setSourceCategories,
    turns,
    savedConversationId,
    savedConversationTitle,
    savedSnapshotNotice,
    markSaved: (id: string | null, title: string) => {
      setSavedConversationId(id);
      setSavedConversationTitle(title);
    },
    restoreSaved: (
      id: string,
      title: string,
      savedTurns: readonly SavedEyeTurn[],
      snapshotNotice: string,
    ) => {
      stop();
      const restored = savedTurns
        .flatMap((turn): EyeChatTurn[] => {
          const turnScope = savedScope(turn.scope);
          const turnReport = savedReport(turn);
          if (turnScope === 'report' && !turnReport) return [];
          return [
            {
              id: ++sequence.current,
              question: turn.question,
              scope: turnScope,
              report: turnReport,
              timeWindow: savedTimeWindow(turn.time_window),
              sourceCategories: savedCategories(turn.source_categories ?? null),
              receivedAt: null,
              saved: true,
              answer: { ...turn.answer, continuation_id: null, model: null },
              status: 'answered',
            },
          ];
        })
        .slice(-8);
      const last = restored.at(-1);
      setTurns(restored);
      setSavedConversationId(id);
      setSavedConversationTitle(title);
      setSavedSnapshotNotice(snapshotNotice);
      setQuestion('');
      setError(null);
      setScope(last?.scope ?? 'global');
      setReport(last?.scope === 'report' ? last.report : null);
      setTimeWindow(last?.timeWindow ?? 'auto');
      setSourceCategories(last?.sourceCategories ?? null);
    },
    busy,
    error,
    send,
    stop,
    clear: () => {
      stop();
      setTurns([]);
      setQuestion('');
      setError(null);
      setScope('global');
      setReport(null);
      setTimeWindow('auto');
      setSourceCategories(null);
      setSavedConversationId(null);
      setSavedConversationTitle('');
      setSavedSnapshotNotice(null);
    },
  };
}
export type EyeChat = ReturnType<typeof useEyeChat>;
