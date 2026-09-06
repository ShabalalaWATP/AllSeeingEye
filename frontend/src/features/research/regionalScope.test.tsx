import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import type { ReportRequest } from '@/lib/api/reports';
import { countries, report } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

function nationChoices() {
  const extras = [
    ['RU', 'Russia'],
    ['CN', 'China'],
    ['IR', 'Iran'],
    ['GB', 'United Kingdom'],
  ].map(([iso2, name]) => ({ ...countries[0], iso2, name }));
  const all = new Map([...countries, ...extras].map((country) => [country.iso2, country]));
  server.use(http.get('/api/countries', () => HttpResponse.json({ items: [...all.values()] })));
}
function captureReport() {
  let body: ReportRequest | undefined;
  server.use(
    http.post('/api/reports', async ({ request }) => {
      body = (await request.json()) as ReportRequest;
      return HttpResponse.json(report, { status: 201 });
    }),
  );
  return () => body;
}

describe('regional and specialist research scope', () => {
  it.each([
    ['Russia', 'RU', ['en', 'ru']],
    ['China', 'CN', ['en', 'zh-CN', 'zh-TW']],
    ['Iran', 'IR', ['en', 'fa']],
  ] as const)(
    'applies %s country and language choices without changing the question or depth',
    async (name, country, languages) => {
      nationChoices();
      const body = captureReport();
      const { user } = renderApp('/research?question=What%20changed%3F', 'user');
      await screen.findByLabelText('Your question');
      await user.click(screen.getByRole('radio', { name: /Detailed/ }));
      await user.click(screen.getByText('Scope and sources'));
      await screen.findByRole('option', { name: 'Iran' });
      await user.click(screen.getByRole('button', { name }));
      expect(screen.getByLabelText('Country')).toHaveValue(country);
      await user.click(screen.getByRole('button', { name: 'Start research' }));
      await waitFor(() =>
        expect(body()).toMatchObject({
          country,
          research_languages: languages,
          question: 'What changed?',
          research_mode: 'detailed',
        }),
      );
    },
  );

  it('constructs an explicit World Bank identifier from labelled controls and preserves it on submission', async () => {
    nationChoices();
    const body = captureReport();
    const { user } = renderApp(
      '/research?country=GB&question=How%20has%20GDP%20changed%3F',
      'user',
    );
    await screen.findByLabelText('Your question');
    await user.click(screen.getByText('Scope and sources'));
    await user.selectOptions(screen.getByLabelText('Record collection'), 'world_bank');
    await user.clear(screen.getByLabelText('First year'));
    await user.type(screen.getByLabelText('First year'), '2020');
    await user.clear(screen.getByLabelText('Last year'));
    await user.type(screen.getByLabelText('Last year'), '2024');
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() =>
      expect(body()).toMatchObject({
        country: 'GB',
        research_focus: 'general',
        research_subject: 'WB:GB:NY.GDP.MKTP.CD:2020:2024',
      }),
    );
  });

  it('requires compatible country scope for scholarly records and retains the explicit subject', async () => {
    nationChoices();
    const body = captureReport();
    const { user } = renderApp('/research?country=GB&question=Review%20recent%20research', 'user');
    await screen.findByLabelText('Your question');
    await user.click(screen.getByText('Scope and sources'));
    await user.selectOptions(screen.getByLabelText('Record collection'), 'academic');
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Choose All countries');
    expect(body()).toBeUndefined();
    await user.selectOptions(screen.getByLabelText('Country'), '');
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() => expect(body()?.research_subject).toBe('academic:'));
  });

  it('shows OONI licence and interpretation limits before submitting a country aggregate request', async () => {
    nationChoices();
    const body = captureReport();
    const { user } = renderApp('/research?country=IR&question=Connectivity%20changes', 'user');
    await screen.findByLabelText('Your question');
    await user.click(screen.getByText('Scope and sources'));
    await user.selectOptions(screen.getByLabelText('Record collection'), 'ooni');
    expect(
      screen.getByText(/Collection requires administrator approval of the source licence/),
    ).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() => expect(body()?.research_subject).toBe('ooni:IR'));
  });

  it('keeps other record identifiers editable when cleared instead of switching modes', async () => {
    const { user } = renderApp('/research', 'user');
    await screen.findByLabelText('Your question');
    await user.click(screen.getByText('Scope and sources'));
    await user.selectOptions(screen.getByLabelText('Record collection'), 'identifier');
    await user.type(screen.getByLabelText('Record identifier'), 'custom-value');
    await user.clear(screen.getByLabelText('Record identifier'));
    expect(screen.getByLabelText('Record identifier')).toHaveValue('');
    expect(screen.getByLabelText('Record collection')).toHaveValue('identifier');
  });
});
