import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { defaultProfile } from '@/test/handlers.profile';
import { plainUser, tokenFor } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

function errorResponse(message: string) {
  return HttpResponse.json({ error: { code: 'invalid_request', message } }, { status: 422 });
}

describe('personal preferences', () => {
  it('edits a display name and region without granting identity or role controls', async () => {
    let body: unknown;
    server.use(
      http.patch('/api/me/profile', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({
          ...defaultProfile,
          display_name: 'Alex Analyst',
          timezone: 'Europe/London',
          date_format: 'iso',
        });
      }),
    );
    const { user } = renderApp('/account', 'user');
    const name = await screen.findByLabelText('Display name');
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
    expect(screen.queryByRole('textbox', { name: /email/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: 'Account role' })).not.toBeInTheDocument();
    await user.clear(name);
    await user.type(name, 'Alex Analyst');
    await user.selectOptions(screen.getByLabelText('Timezone'), 'Europe/London');
    await user.selectOptions(screen.getByLabelText('Date format'), 'iso');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByText('Your preferences have been saved.')).toBeVisible();
    expect(body).toEqual({
      display_name: 'Alex Analyst',
      timezone: 'Europe/London',
      date_format: 'iso',
    });
    expect(useAuthStore.getState().user?.display_name).toBe('Alex Analyst');
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
  });

  it('resets unsaved edits and retains the form after a save failure', async () => {
    server.use(
      http.patch('/api/me/profile', () => errorResponse('The display name was not accepted.')),
    );
    const { user } = renderApp('/account', 'user');
    const name = await screen.findByLabelText('Display name');
    await user.clear(name);
    await user.type(name, 'Changed');
    await user.click(screen.getByRole('button', { name: 'Reset changes' }));
    expect(name).toHaveValue(defaultProfile.display_name);
    await user.clear(name);
    await user.type(name, 'Retry name');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The display name was not accepted.',
    );
    expect(name).toHaveValue('Retry name');
  });

  it('validates source language codes and saves only research defaults', async () => {
    let body: unknown;
    server.use(
      http.patch('/api/me/profile', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...defaultProfile, ...(body as object) });
      }),
    );
    const { user } = renderApp('/account?section=research', 'user');
    const input = await screen.findByLabelText('Source languages');
    await user.clear(input);
    await user.type(input, 'not a code');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(screen.getByRole('alert')).toHaveTextContent('valid language codes');
    expect(body).toBeUndefined();
    await user.clear(input);
    await user.type(input, 'en, fr, en');
    await user.selectOptions(screen.getByLabelText('Research depth'), 'detailed');
    await user.selectOptions(screen.getByLabelText('Default date window'), '7');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByText('Your preferences have been saved.')).toBeVisible();
    expect(body).toEqual({
      research_languages: ['en', 'fr'],
      research_mode: 'detailed',
      research_window_days: 7,
      research_country: null,
    });
  });

  it('saves report presentation independently of evidence policy', async () => {
    let body: unknown;
    server.use(
      http.patch('/api/me/profile', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...defaultProfile, ...(body as object) });
      }),
    );
    const { user } = renderApp('/account?section=reports', 'user');
    await user.selectOptions(await screen.findByLabelText('Narrative language'), 'fr');
    await user.selectOptions(screen.getByLabelText('Report style'), 'briefing');
    await user.selectOptions(screen.getByLabelText('Preferred export format'), 'docx');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByText('Your preferences have been saved.')).toBeVisible();
    expect(body).toEqual({
      report_language: 'fr',
      report_style: 'briefing',
      export_format: 'docx',
    });
    expect(
      screen.getByText('Mechanically checked judgement statements remain in English.'),
    ).toBeVisible();
  });

  it('offers a retry when loading fails', async () => {
    server.use(http.get('/api/me/profile', () => errorResponse('Preferences unavailable.')));
    const { user } = renderApp('/account', 'user');
    expect(await screen.findByRole('alert')).toHaveTextContent('Preferences unavailable.');
    server.use(http.get('/api/me/profile', () => HttpResponse.json(defaultProfile)));
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByLabelText('Display name')).toBeVisible();
  });

  it('does not apply an earlier save to a replacement identity', async () => {
    let release: () => void = () => undefined;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    let started = false;
    server.use(
      http.patch('/api/me/profile', async () => {
        started = true;
        await pending;
        return HttpResponse.json({ ...defaultProfile, display_name: 'Old identity update' });
      }),
    );
    const { user } = renderApp('/account', 'user');
    await user.type(await screen.findByLabelText('Display name'), ' changed');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    await waitFor(() => expect(started).toBe(true));
    const replacement = {
      ...plainUser,
      id: '99999999-9999-4999-8999-999999999999',
      display_name: 'New identity',
    };
    server.use(
      http.get('/api/me/profile', () =>
        HttpResponse.json({ ...defaultProfile, display_name: 'New identity' }),
      ),
    );
    act(() => useAuthStore.getState().setSession(tokenFor(replacement)));
    await act(async () => {
      release();
      await pending;
    });
    await waitFor(() => expect(screen.getByLabelText('Display name')).toHaveValue('New identity'));
    expect(useAuthStore.getState().user?.display_name).toBe('New identity');
  });
  it.each(['ar', 'zh'])(
    'warns about PDF text support for %s and clears the warning for Word',
    async (language) => {
      const { user } = renderApp('/account?section=reports', 'user');
      await user.selectOptions(await screen.findByLabelText('Narrative language'), language);
      expect(screen.getByText(/PDF downloads cannot currently display/)).toBeVisible();
      await user.selectOptions(screen.getByLabelText('Preferred export format'), 'docx');
      expect(screen.queryByText(/PDF downloads cannot currently display/)).not.toBeInTheDocument();
    },
  );
});
