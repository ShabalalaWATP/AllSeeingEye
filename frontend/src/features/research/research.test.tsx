import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { countries, plainUser, report, tokenFor } from '@/test/fixtures';
import { setupTeams, team } from '@/test/fixtures.teams';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('question-led research', () => {
  it('waits for a contextual country lookup instead of rejecting its still-loading scope', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.get('/api/countries', async () => {
        await gate;
        return HttpResponse.json({ items: countries });
      }),
    );
    renderApp('/research?question=What%20changed%3F&country=UA', 'user');
    expect(await screen.findByText('Loading country scope')).toBeVisible();
    await waitFor(() =>
      expect(screen.queryByText('Loading research options')).not.toBeInTheDocument(),
    );
    expect(screen.getByRole('button', { name: 'Start research' })).toBeDisabled();
    release();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Start research' })).toBeEnabled(),
    );
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('submits a contextual quick question using the Ask the Eye template and opens its saved report', async () => {
    let body: unknown;
    server.use(
      http.post('/api/reports', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(report, { status: 201 });
      }),
    );
    const { user, router } = renderApp(
      '/research?question=What%20changed%20in%20Ukraine%3F&country=ua',
      'user',
    );
    expect(await screen.findByRole('heading', { name: 'Research' })).toBeVisible();
    expect(await screen.findByLabelText('Your question')).toHaveValue('What changed in Ukraine?');
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Start research' })).toBeEnabled(),
    );
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(`/reports/${report.report.id}`),
    );
    expect(body).toEqual({
      disclose_area_to_provider: false,
      template: 'ask',
      question: 'What changed in Ukraine?',
      country: 'UA',
      window_hours: 72,
      report_language: 'en',
      report_style: 'assessment',
      research_mode: 'quick',
      research_languages: ['en'],
      research_focus: 'general',
      research_subject: null,
      devils_advocacy: false,
    });
  });

  it('submits detailed company research with explicit team, languages and advocacy', async () => {
    setupTeams();
    let body: unknown;
    server.use(
      http.post('/api/reports', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(report, { status: 201 });
      }),
    );
    const { user } = renderApp('/research?country=UA');
    await user.type(
      await screen.findByLabelText('Your question'),
      'Assess recent changes at Example Company.',
    );
    await user.click(screen.getByRole('radio', { name: /Detailed/ }));
    await user.click(screen.getByText('Scope and sources'));
    await screen.findByRole('option', { name: `Team: ${team.name}` });
    await user.selectOptions(screen.getByLabelText('Workspace'), team.id);
    expect(screen.getByLabelText('Country')).toHaveValue('UA');
    await user.selectOptions(screen.getByLabelText('Research focus'), 'company');
    expect(screen.queryByLabelText('Country')).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Research focus'), 'general');
    expect(screen.getByLabelText('Country')).toHaveValue('');
    await user.selectOptions(screen.getByLabelText('Research focus'), 'company');
    await user.type(screen.getByLabelText('Company name'), 'Example Company, UK');
    await user.selectOptions(screen.getByLabelText('Reporting window'), '168');
    await user.click(screen.getByLabelText('French'));
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() =>
      expect(body).toEqual({
        disclose_area_to_provider: false,
        template: 'ask',
        question: 'Assess recent changes at Example Company.',
        window_hours: 168,
        report_language: 'en',
        report_style: 'assessment',
        research_mode: 'detailed',
        research_languages: ['en', 'fr'],
        research_focus: 'company',
        research_subject: 'Example Company, UK',
        devils_advocacy: true,
        team_id: team.id,
      }),
    );
  });

  it('validates empty questions, language selection and explicit domain subjects without sending', async () => {
    let requests = 0;
    server.use(
      http.post('/api/reports', () => {
        requests++;
        return HttpResponse.json(report);
      }),
    );
    const { user } = renderApp('/research', 'user');
    const button = await screen.findByRole('button', { name: 'Start research' });
    await waitFor(() => expect(button).toBeEnabled());
    await user.click(button);
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a question to research.');
    await user.type(screen.getByLabelText('Your question'), 'Assess this domain.');
    await user.click(screen.getByText('Scope and sources'));
    await user.click(screen.getByLabelText('English'));
    await user.click(button);
    expect(screen.getByRole('alert')).toHaveTextContent('Select at least one search language.');
    await user.click(screen.getByLabelText('English'));
    await user.selectOptions(screen.getByLabelText('Research focus'), 'domain');
    await user.click(button);
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a domain name.');
    expect(requests).toBe(0);
  });

  it('does not silently discard an unavailable country supplied in the URL', async () => {
    const { user } = renderApp('/research?question=What%20changed%3F&country=ZZ', 'user');
    const button = await screen.findByRole('button', { name: 'Start research' });
    await waitFor(() => expect(button).toBeEnabled());
    await user.click(button);
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Choose an available country or all countries.',
    );
    expect(screen.getByLabelText('Country')).toBeVisible();
    expect(screen.getByLabelText('Country')).toHaveValue('ZZ');
  });

  it('keeps a single pending request, shows real busy state, and preserves input after failure', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let requests = 0;
    server.use(
      http.post('/api/reports', async () => {
        requests++;
        await gate;
        return HttpResponse.json(
          { error: { code: 'research_unavailable', message: 'Research sources are unavailable.' } },
          { status: 503 },
        );
      }),
    );
    const { user } = renderApp('/research', 'user');
    await user.type(await screen.findByLabelText('Your question'), 'What changed in the past day?');
    const form = screen.getByRole('form', { name: 'Research a question' });
    act(() => {
      fireEvent.submit(form);
      fireEvent.submit(form);
    });
    expect(await screen.findByText('Starting research')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Start research' })).toBeDisabled();
    expect(screen.getByLabelText('Your question')).toBeDisabled();
    await waitFor(() => expect(requests).toBe(1));
    release();
    expect(await screen.findByRole('alert')).toHaveTextContent('Research sources are unavailable.');
    expect(screen.getByLabelText('Your question')).toHaveValue('What changed in the past day?');
    expect(screen.getByRole('button', { name: 'Start research' })).toBeEnabled();
  });

  it('does not redirect a replacement account when an old request finishes', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let requests = 0;
    server.use(
      http.post('/api/reports', async () => {
        requests++;
        await gate;
        return HttpResponse.json(report);
      }),
    );
    const { user, router } = renderApp('/research?question=What%20changed%3F', 'user');
    const button = await screen.findByRole('button', { name: 'Start research' });
    await waitFor(() => expect(button).toBeEnabled());
    await user.click(button);
    await waitFor(() => expect(requests).toBe(1));
    act(() =>
      useAuthStore
        .getState()
        .setSession(tokenFor({ ...plainUser, id: '33333333-3333-4333-8333-333333333333' })),
    );
    await act(async () => {
      release();
      await gate;
    });
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Start research' })).toBeEnabled(),
    );
    expect(router.state.location.pathname).toBe('/research');
  });

  it('handles missing products and allows a failed product lookup to be retried', async () => {
    server.use(
      http.get('/api/reports/templates', () =>
        HttpResponse.json(
          { error: { code: 'server_error', message: 'Options unavailable.' } },
          { status: 500 },
        ),
      ),
    );
    const { user } = renderApp('/research', 'user');
    expect(await screen.findByRole('alert')).toHaveTextContent('Options unavailable.');
    expect(screen.getByRole('button', { name: 'Start research' })).toBeDisabled();
    server.use(http.get('/api/reports/templates', () => HttpResponse.json({ items: [] })));
    await user.click(screen.getByRole('button', { name: 'Retry research options' }));
    expect(await screen.findByText(/Ask the Eye product is not configured/)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Start research' })).toBeDisabled();
  });

  it('is reachable from navigation and keeps the globe route intact', async () => {
    const { user, router } = renderApp('/research', 'user');
    await screen.findByRole('heading', { name: 'Research' });
    const nav = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(nav).getByRole('link', { name: 'Research' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(nav).queryByRole('link', { name: 'Users' })).not.toBeInTheDocument();
    await user.click(within(nav).getByRole('button', { name: /Globe/ }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });

  it('requires sign-in before showing research controls', async () => {
    renderApp('/research', 'anonymous');
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeVisible();
    expect(screen.queryByRole('form', { name: 'Research a question' })).not.toBeInTheDocument();
  });
});
