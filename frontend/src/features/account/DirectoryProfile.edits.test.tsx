import { fireEvent, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import type { DirectoryProfile as DirectoryProfileData } from '@/lib/api/directoryProfile';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { DirectoryProfile } from './DirectoryProfile';

const empty: DirectoryProfileData = {
  user_id: '0f0e0d0c-0b0a-4908-8706-050403020100',
  username: null,
  job_title: null,
  organisation: null,
  biography: null,
  country: null,
  languages: [],
  expertise: [],
  timezone: null,
  is_discoverable: false,
  visible_fields: [],
  avatar_url: null,
  revision: 1,
  updated_at: null,
};

describe('directory profile edits', () => {
  it('renders an empty profile with defaults and ignores an unchanged submission', async () => {
    let patches = 0;
    server.use(
      http.get('/api/me/directory-profile', () => HttpResponse.json(empty)),
      http.patch('/api/me/directory-profile', () => {
        patches += 1;
        return HttpResponse.json(empty);
      }),
    );
    render(<DirectoryProfile />);
    expect(await screen.findByLabelText('Username')).toHaveValue('');
    expect(screen.getByRole('textbox', { name: 'Job title' })).toHaveValue('');
    expect(screen.getByRole('textbox', { name: 'Organisation' })).toHaveValue('');
    expect(screen.getByLabelText(/Country code/)).toHaveValue('');
    expect(screen.getByRole('combobox', { name: 'Timezone' })).toHaveValue('UTC');
    expect(screen.getByRole('button', { name: 'Reset' })).toBeDisabled();

    fireEvent.submit(screen.getByRole('form', { name: 'Directory profile' }));
    expect(patches).toBe(0);
  });

  it('normalises blank text and lists, reports a failure and saves on retry', async () => {
    const bodies: Record<string, unknown>[] = [];
    server.use(
      http.get('/api/me/directory-profile', () => HttpResponse.json(empty)),
      http.patch('/api/me/directory-profile', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        bodies.push(body);
        if (bodies.length === 1) {
          return apiError(409, 'conflict', 'That username is already taken.');
        }
        return HttpResponse.json({ ...empty, biography: 'Maritime analyst', revision: 2 });
      }),
    );
    const user = userEvent.setup();
    render(<DirectoryProfile />);
    const username = await screen.findByLabelText('Username');
    await user.type(username, '  Taken_Name ');
    await user.type(screen.getByLabelText(/Country code/), '  ');
    await user.type(screen.getByRole('textbox', { name: 'Biography' }), '  Maritime analyst  ');
    await user.type(screen.getByRole('textbox', { name: /Languages/ }), 'en');
    await user.click(screen.getByRole('checkbox', { name: 'Show me in directory search' }));
    await user.click(screen.getByRole('button', { name: 'Save directory profile' }));

    expect(await screen.findByText('That username is already taken.')).toBeVisible();
    expect(bodies[0]).toMatchObject({
      username: 'taken_name',
      job_title: null,
      country: null,
      biography: 'Maritime analyst',
      languages: ['en'],
      expertise: [],
      timezone: null,
      is_discoverable: true,
      expected_revision: 1,
    });

    await user.clear(username);
    expect(screen.queryByText('That username is already taken.')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Save directory profile' }));
    expect(await screen.findByText('Directory profile saved.')).toBeVisible();
    expect(bodies[1]).toMatchObject({ username: null, biography: 'Maritime analyst' });
    expect(screen.getByRole('textbox', { name: 'Biography' })).toHaveValue('Maritime analyst');
  });

  it('resets unsaved edits back to the loaded profile', async () => {
    server.use(http.get('/api/me/directory-profile', () => HttpResponse.json(empty)));
    const user = userEvent.setup();
    render(<DirectoryProfile />);
    await user.type(await screen.findByRole('textbox', { name: 'Job title' }), 'Lead');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Timezone' }), 'Europe/London');
    await user.click(screen.getByRole('button', { name: 'Reset' }));
    expect(screen.getByRole('textbox', { name: 'Job title' })).toHaveValue('');
    expect(screen.getByRole('combobox', { name: 'Timezone' })).toHaveValue('UTC');
    expect(screen.getByRole('button', { name: 'Save directory profile' })).toBeDisabled();
  });
});
