import { act, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';

import { applySession } from '@/test/render';
import { server } from '@/test/server';

import { eyeAnswer } from './assistantFixture';
import { EyeAssistant } from './EyeAssistant';
import { EYE_STATUS_TEXT, nextEyeStatus, type EyeStatusState } from './eyeStatus';
import type { EyeChatTurn } from './useEyeChat';

const observers: MutationObserver[] = [];
afterEach(() => {
  for (const observer of observers.splice(0)) observer.disconnect();
});

/** The single persistent Eye status region, which must sit outside the launcher button. */
function statusRegion(): HTMLElement {
  const region = document.querySelector<HTMLElement>('[data-eye-status]');
  if (!region) throw new Error('Eye status region missing');
  return region;
}

/** Every distinct text the live region has held, in order: one entry per announcement. */
function recordAnnouncements(region: HTMLElement): string[] {
  const seen: string[] = [];
  const record = () => {
    const text = region.textContent;
    if (text && seen.at(-1) !== text) seen.push(text);
  };
  const observer = new MutationObserver(record);
  observer.observe(region, { childList: true, characterData: true, subtree: true });
  observers.push(observer);
  return seen;
}

function gatedAnswer(response: () => Response) {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.post('/api/assistant/answer', async () => {
      await gate;
      return response();
    }),
  );
  return async () => {
    await act(async () => {
      release();
      await gate;
    });
  };
}

async function askThenMinimise(question: string) {
  applySession('user');
  const view = render(
    <MemoryRouter>
      <EyeAssistant />
    </MemoryRouter>,
  );
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Ask Eye', expanded: false }));
  const announcements = recordAnnouncements(statusRegion());
  await user.type(screen.getByLabelText('Ask the Eye'), `${question}{Enter}`);
  await user.click(screen.getByRole('button', { name: 'Minimise chat window' }));
  return { user, view, announcements };
}

describe('Eye status announcements', () => {
  it('announces answering then ready once while the panel is closed, without replaying', async () => {
    const release = gatedAnswer(() => HttpResponse.json(eyeAnswer));
    const { user, view, announcements } = await askThenMinimise('Answer while closed');
    const region = statusRegion();
    expect(region).toHaveAttribute('aria-live', 'polite');
    expect(region.closest('button')).toBeNull();
    expect(region).toHaveTextContent(EYE_STATUS_TEXT.pending);
    await release();
    expect(region).toHaveTextContent(EYE_STATUS_TEXT.answered);
    // Opening the panel, closing it and rerendering keep the same text: nothing is replayed.
    await user.click(screen.getByRole('button', { name: 'Ask Eye', expanded: false }));
    expect(screen.getByText('Two recent vessel observations are available.')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Minimise chat window' }));
    view.rerender(
      <MemoryRouter>
        <EyeAssistant />
      </MemoryRouter>,
    );
    expect(announcements).toEqual([EYE_STATUS_TEXT.pending, EYE_STATUS_TEXT.answered]);
  });

  it('announces a failure as a failure, never as ready', async () => {
    const release = gatedAnswer(() =>
      HttpResponse.json(
        { error: { code: 'unavailable', message: 'AI connection unavailable.' } },
        { status: 503 },
      ),
    );
    const { announcements } = await askThenMinimise('Fail while closed');
    await release();
    expect(statusRegion()).toHaveTextContent(EYE_STATUS_TEXT.failed);
    expect(announcements).toEqual([EYE_STATUS_TEXT.pending, EYE_STATUS_TEXT.failed]);
  });

  it('keeps the launcher name stable and its visual indicators out of the accessibility tree', async () => {
    const release = gatedAnswer(() => HttpResponse.json(eyeAnswer));
    await askThenMinimise('Indicator check');
    const launcher = screen.getByRole('button', { name: 'Ask Eye', expanded: false });
    expect(launcher.querySelector('[role="status"], [aria-live]')).toBeNull();
    await release();
    expect(screen.getByRole('button', { name: 'Ask Eye', expanded: false })).toBe(launcher);
    expect(launcher.querySelector('[role="status"], [aria-live]')).toBeNull();
  });
});

function turn(id: number, status: EyeChatTurn['status']): EyeChatTurn {
  return {
    id,
    question: 'Q',
    scope: 'global',
    report: null,
    timeWindow: 'auto',
    sourceCategories: null,
    receivedAt: null,
    saved: status !== 'pending',
    answer: null,
    status,
  };
}

describe('Eye status transitions', () => {
  const empty: EyeStatusState = { turnId: null, status: null, live: false, message: '' };

  it('announces each live state once and keeps the same state object when nothing changed', () => {
    const pending = nextEyeStatus(empty, turn(1, 'pending'));
    expect(pending.message).toBe(EYE_STATUS_TEXT.pending);
    expect(nextEyeStatus(pending, turn(1, 'pending'))).toBe(pending);
    const stopped = nextEyeStatus(pending, turn(1, 'stopped'));
    expect(stopped.message).toBe(EYE_STATUS_TEXT.stopped);
    expect(nextEyeStatus(stopped, turn(1, 'stopped'))).toBe(stopped);
  });

  it('does not announce a restored saved answer that never ran in this session', () => {
    const restored = nextEyeStatus(empty, turn(4, 'answered'));
    expect(restored.message).toBe('');
  });

  it('clears the status for a new chat without announcing anything', () => {
    const answered = nextEyeStatus(nextEyeStatus(empty, turn(1, 'pending')), turn(1, 'answered'));
    expect(nextEyeStatus(answered, undefined).message).toBe('');
    expect(nextEyeStatus(empty, undefined)).toBe(empty);
  });
});
