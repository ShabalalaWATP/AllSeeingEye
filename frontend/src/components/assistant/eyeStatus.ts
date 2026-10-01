import { useState } from 'react';

import type { EyeChatTurn } from './useEyeChat';

/** What the persistent Eye status region says for each state of the latest question. */
export const EYE_STATUS_TEXT: Record<EyeChatTurn['status'], string> = {
  pending: 'Eye is answering your question.',
  answered: "Eye's answer is ready.",
  failed: 'Eye could not answer your question.',
  stopped: 'Eye stopped. No answer was added.',
};

export interface EyeStatusState {
  turnId: number | null;
  status: EyeChatTurn['status'] | null;
  /** The turn was asked in this session, so its outcome is news worth announcing. */
  live: boolean;
  message: string;
}

const EMPTY: EyeStatusState = { turnId: null, status: null, live: false, message: '' };

/**
 * Move the status on only when the latest question changes state. The same state returns
 * the same object, so rerenders and opening the panel never replay an announcement, and a
 * restored saved answer that never ran here stays silent.
 */
export function nextEyeStatus(
  previous: EyeStatusState,
  latest: EyeChatTurn | undefined,
): EyeStatusState {
  if (!latest) return previous.turnId === null && previous.message === '' ? previous : EMPTY;
  if (latest.id === previous.turnId && latest.status === previous.status) return previous;
  const live = latest.status === 'pending' || (latest.id === previous.turnId && previous.live);
  return {
    turnId: latest.id,
    status: latest.status,
    live,
    message: live ? EYE_STATUS_TEXT[latest.status] : '',
  };
}

/** The text for the one persistent, polite Eye status region. */
export function useEyeStatus(turns: readonly EyeChatTurn[]): string {
  const [state, setState] = useState(EMPTY);
  const next = nextEyeStatus(state, turns.at(-1));
  // Derived during render: React re-renders at once without committing the stale text.
  if (next !== state) setState(next);
  return next.message;
}
