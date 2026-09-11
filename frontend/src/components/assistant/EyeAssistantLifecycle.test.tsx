import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { applySession } from '@/test/render';
import { plainUser, tokenFor } from '@/test/fixtures';
import { server } from '@/test/server';
import { useAuthStore } from '@/stores/auth';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import type { AssistantRequest } from '@/lib/api/assistant';
import { EyeAssistant } from './EyeAssistant';
import { eyeAnswer } from './assistantFixture';

async function mount() {
  applySession('user');
  const result = render(
    <MemoryRouter>
      <EyeAssistant />
    </MemoryRouter>,
  );
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
  return { ...result, user };
}

it.each(['access', 'account', 'logout'] as const)(
  'clears conversation and rejects late answers after %s changes',
  async (change) => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let started = false;
    server.use(
      http.post('/api/assistant/answer', async () => {
        started = true;
        await gate;
        return HttpResponse.json(eyeAnswer);
      }),
    );
    const { user } = await mount();
    await user.type(screen.getByLabelText('Ask the Eye'), 'Private operator question.{Enter}');
    await waitFor(() => expect(started).toBe(true));
    act(() => {
      if (change === 'access') invalidateWorkspaceAccess();
      else if (change === 'logout') useAuthStore.getState().clearSession();
      else
        useAuthStore
          .getState()
          .setSession(tokenFor({ ...plainUser, id: '77777777-7777-4777-8777-777777777777' }));
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await act(async () => {
      release();
      await gate;
    });
    if (change !== 'logout') {
      await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
      expect(screen.getByText('What would you like to know?')).toBeVisible();
    }
    expect(screen.queryByText('Private operator question.')).not.toBeInTheDocument();
    expect(
      screen.queryByText('Two recent vessel observations are available.'),
    ).not.toBeInTheDocument();
  },
);

it('prevents duplicate sends, stops a request and allows a new question without admitting the old result', async () => {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const bodies: AssistantRequest[] = [];
  server.use(
    http.post('/api/assistant/answer', async ({ request }) => {
      bodies.push((await request.json()) as AssistantRequest);
      if (bodies.length === 1) await gate;
      return HttpResponse.json(eyeAnswer);
    }),
  );
  const { user } = await mount();
  await user.type(screen.getByLabelText('Ask the Eye'), 'First question');
  const form = screen.getByRole('button', { name: 'Ask Eye' }).closest('form')!;
  act(() => {
    fireEvent.submit(form);
    fireEvent.submit(form);
  });
  await waitFor(() => expect(bodies).toHaveLength(1));
  expect(screen.getByLabelText('Ask the Eye')).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Stop' }));
  expect(screen.getByText('Stopped. No answer was added.')).toBeVisible();
  await user.type(screen.getByLabelText('Ask the Eye'), 'Second question{Enter}');
  await screen.findByText('Two recent vessel observations are available.');
  expect(bodies[1]?.prior_questions).toEqual([]);
  await act(async () => {
    release();
    await gate;
  });
  expect(screen.getAllByText('Two recent vessel observations are available.')).toHaveLength(1);
});

it('sends only the last four successful user questions and New chat discards history', async () => {
  const bodies: AssistantRequest[] = [];
  server.use(
    http.post('/api/assistant/answer', async ({ request }) => {
      bodies.push((await request.json()) as AssistantRequest);
      return HttpResponse.json(eyeAnswer);
    }),
  );
  const { user } = await mount();
  for (let index = 1; index <= 6; index++) {
    await user.type(screen.getByLabelText('Ask the Eye'), `Question ${index}{Enter}`);
    await waitFor(() => expect(screen.getByLabelText('Ask the Eye')).toBeEnabled());
  }
  expect(bodies[5]?.prior_questions).toEqual([
    'Question 2',
    'Question 3',
    'Question 4',
    'Question 5',
  ]);
  expect(bodies[5]).not.toHaveProperty('messages');
  await user.click(screen.getByRole('button', { name: 'New chat' }));
  expect(screen.queryByText('Question 6')).not.toBeInTheDocument();
  await user.type(screen.getByLabelText('Ask the Eye'), 'Fresh question{Enter}');
  await waitFor(() => expect(bodies).toHaveLength(7));
  expect(bodies[6]?.prior_questions).toEqual([]);
});

it('keeps unsafe markup and URLs inert and offers a retry after a failed answer', async () => {
  let calls = 0;
  server.use(
    http.post('/api/assistant/answer', () => {
      calls++;
      if (calls === 1)
        return HttpResponse.json(
          { error: { code: 'unavailable', message: 'AI connection unavailable.' } },
          { status: 503 },
        );
      return HttpResponse.json({
        ...eyeAnswer,
        paragraphs: [
          { kind: 'finding', text: '<img src=x onerror=alert(1)>', citations: ['E1', 'UNKNOWN'] },
        ],
        sources: [{ ...eyeAnswer.sources[0], url: 'javascript:alert(1)' }],
      });
    }),
  );
  const { user } = await mount();
  await user.type(screen.getByLabelText('Ask the Eye'), 'Retry me{Enter}');
  expect(await screen.findByRole('alert')).toHaveTextContent('AI connection unavailable');
  expect(screen.getByLabelText('Ask the Eye')).toHaveValue('Retry me');
  await user.click(screen.getByRole('button', { name: 'Ask Eye' }));
  expect(await screen.findByText('<img src=x onerror=alert(1)>')).toBeVisible();
  expect(document.querySelector('[onerror]')).toBeNull();
  expect(document.querySelector('a[href^="javascript:"]')).toBeNull();
});

it('closing the panel cancels unfinished work and retains only already displayed turns', async () => {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.post('/api/assistant/answer', async () => {
      await gate;
      return HttpResponse.json(eyeAnswer);
    }),
  );
  const { user } = await mount();
  await user.type(screen.getByLabelText('Ask the Eye'), 'Stop on close{Enter}');
  await user.click(screen.getByRole('button', { name: 'Close Eye assistant' }));
  await act(async () => {
    release();
    await gate;
  });
  await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
  expect(screen.getByText('Stopped. No answer was added.')).toBeVisible();
  expect(
    screen.queryByText('Two recent vessel observations are available.'),
  ).not.toBeInTheDocument();
});
