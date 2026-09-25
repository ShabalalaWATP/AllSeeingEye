import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import { EyeAssistant } from '@/components/assistant/EyeAssistant';
import { mountAreaPanel } from '@/test/areaResearchPanel';
import { applySession, renderApp } from '@/test/render';
import { server } from '@/test/server';

import { AI_RESEARCH_UNAVAILABLE } from './AiResearchNotice';

function capabilities(aiResearch: boolean | undefined) {
  let requests = 0;
  server.use(
    http.get('/api/capabilities', () => {
      requests += 1;
      return HttpResponse.json({
        os_maps: false,
        os_layers: [],
        ...(aiResearch === undefined ? {} : { ai_research: aiResearch }),
      });
    }),
  );
  return () => requests;
}

describe('research page', () => {
  it('explains up front, in plain English, that AI research is not set up', async () => {
    capabilities(false);
    const { user } = renderApp('/research', 'user');
    const notice = await screen.findByText(AI_RESEARCH_UNAVAILABLE);
    expect(notice).toBeVisible();
    // Ordinary accounts are told who can fix it, without a link they cannot use.
    expect(screen.queryByRole('link', { name: 'Connect an AI provider' })).not.toBeInTheDocument();
    // The notice never blocks the form; submission still reports its own failures.
    const form = within(await screen.findByRole('form', { name: 'Research a question' }));
    await user.type(form.getByLabelText('Your question'), 'What changed?');
    await waitFor(() => expect(form.getByRole('button', { name: 'Start research' })).toBeEnabled());
  });

  it('links administrators to the AI connection page', async () => {
    capabilities(false);
    renderApp('/research', 'admin');
    const link = await screen.findByRole('link', { name: 'Connect an AI provider' });
    expect(link).toHaveAttribute('href', '/admin/llm');
    expect(screen.getByText(AI_RESEARCH_UNAVAILABLE)).toBeVisible();
  });

  it.each([
    ['ready', true],
    ['unknown', undefined],
  ] as const)('shows no notice when research is %s', async (_label, value) => {
    const requests = capabilities(value);
    renderApp('/research', 'user');
    await screen.findByRole('form', { name: 'Research a question' });
    await waitFor(() => expect(requests()).toBeGreaterThan(0));
    expect(screen.queryByText(AI_RESEARCH_UNAVAILABLE)).not.toBeInTheDocument();
  });

  it('shows no notice when the capability check fails', async () => {
    server.use(
      http.get('/api/capabilities', () =>
        HttpResponse.json({ error: { code: 'x', message: 'Down.' } }, { status: 500 }),
      ),
    );
    renderApp('/research', 'user');
    await screen.findByRole('form', { name: 'Research a question' });
    expect(screen.queryByText(AI_RESEARCH_UNAVAILABLE)).not.toBeInTheDocument();
  });
});

describe('Eye assistant', () => {
  async function openEye(session: 'user' | 'admin') {
    applySession(session);
    render(
      <MemoryRouter>
        <EyeAssistant />
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
    return user;
  }

  it('shows the notice before a question is asked and keeps the composer usable', async () => {
    capabilities(false);
    const user = await openEye('user');
    const dialog = within(screen.getByRole('dialog', { name: 'Eye assistant' }));
    expect(await dialog.findByText(AI_RESEARCH_UNAVAILABLE)).toBeVisible();
    expect(dialog.queryByRole('link', { name: 'Connect an AI provider' })).not.toBeInTheDocument();
    await user.type(dialog.getByLabelText('Ask the Eye'), 'Anything new?');
    expect(dialog.getByRole('button', { name: /Ask Eye/ })).toBeEnabled();
  });

  it('gives administrators the set-up link and closes the panel when it is followed', async () => {
    capabilities(false);
    const user = await openEye('admin');
    await user.click(await screen.findByRole('link', { name: 'Connect an AI provider' }));
    expect(screen.queryByRole('dialog', { name: 'Eye assistant' })).not.toBeInTheDocument();
  });

  it('stays quiet when AI research is ready', async () => {
    const requests = capabilities(true);
    await openEye('user');
    await waitFor(() => expect(requests()).toBe(1));
    expect(screen.queryByText(AI_RESEARCH_UNAVAILABLE)).not.toBeInTheDocument();
  });
});

describe('map area research panel', () => {
  it('shows the notice above the area steps without disabling source checks', async () => {
    capabilities(false);
    applySession('user');
    mountAreaPanel();
    expect(await screen.findByText(AI_RESEARCH_UNAVAILABLE)).toBeVisible();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Check sources' })).toBeEnabled(),
    );
  });

  it('stays quiet when AI research is ready', async () => {
    const requests = capabilities(true);
    applySession('user');
    mountAreaPanel();
    await waitFor(() => expect(requests()).toBe(1));
    expect(screen.queryByText(AI_RESEARCH_UNAVAILABLE)).not.toBeInTheDocument();
  });
});
