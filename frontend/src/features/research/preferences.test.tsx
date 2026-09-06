import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { useProfileStore } from '@/stores/profile';
import { defaultProfile } from '@/test/handlers.profile';
import { report } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it('loads defaults before editing, honours URL scope and preserves edits after preferences refresh', async () => {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let body: unknown;
  server.use(
    http.get('/api/me/profile', async () => {
      await gate;
      return HttpResponse.json({
        ...defaultProfile,
        research_mode: 'detailed',
        research_country: 'GB',
        research_window_days: 7,
        research_languages: ['fr'],
        report_language: 'fr',
        report_style: 'briefing',
      });
    }),
    http.post('/api/reports', async ({ request }) => {
      body = await request.json();
      return HttpResponse.json(report, { status: 201 });
    }),
  );
  const { user } = renderApp('/research?country=UA&question=What%20changed%3F', 'user');
  expect(await screen.findByText('Loading your research defaults')).toBeVisible();
  expect(screen.queryByLabelText('Your question')).not.toBeInTheDocument();
  release();
  expect(await screen.findByLabelText('Narrative language')).toHaveValue('fr');
  expect(screen.getByLabelText('Report style')).toHaveValue('briefing');
  expect(screen.getByRole('radio', { name: /Detailed/ })).toBeChecked();
  await user.click(screen.getByText('Scope and sources'));
  expect(screen.getByLabelText('Country')).toHaveValue('UA');
  expect(screen.getByLabelText('Reporting window')).toHaveValue('168');
  await user.selectOptions(screen.getByLabelText('Narrative language'), 'de');
  await user.selectOptions(screen.getByLabelText('Report style'), 'assessment');
  await act(async () => {
    await useProfileStore.getState().reload();
  });
  expect(screen.getByLabelText('Narrative language')).toHaveValue('de');
  await waitFor(() => expect(screen.getByRole('button', { name: 'Start research' })).toBeEnabled());
  await user.click(screen.getByRole('button', { name: 'Start research' }));
  await waitFor(() =>
    expect(body).toMatchObject({
      country: 'UA',
      window_hours: 168,
      research_languages: ['fr'],
      research_mode: 'detailed',
      report_language: 'de',
      report_style: 'assessment',
    }),
  );
});

it('offers a retry when preferences cannot load without silently applying different defaults', async () => {
  server.use(http.get('/api/me/profile', () => new HttpResponse(null, { status: 503 })));
  const { user } = renderApp('/research', 'user');
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Research defaults could not be loaded',
  );
  expect(screen.queryByLabelText('Your question')).not.toBeInTheDocument();
  server.use(http.get('/api/me/profile', () => HttpResponse.json(defaultProfile)));
  await user.click(screen.getByRole('button', { name: 'Retry preferences' }));
  expect(await screen.findByLabelText('Your question')).toBeVisible();
});
