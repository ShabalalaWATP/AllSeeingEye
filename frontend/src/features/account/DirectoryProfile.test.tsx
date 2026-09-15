import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { DirectoryProfile as DirectoryProfileData } from '@/lib/api/directoryProfile';
import { server } from '@/test/server';

import { DirectoryProfile } from './DirectoryProfile';

const USER_ID = '0f0e0d0c-0b0a-4908-8706-050403020100';
const AVATAR = `/api/directory/users/${USER_ID}/avatar?v=0123456789abcdef`;

function profile(overrides: Partial<DirectoryProfileData> = {}): DirectoryProfileData {
  return {
    user_id: USER_ID,
    username: 'field_lead',
    job_title: 'Analyst',
    organisation: 'Open Desk',
    biography: null,
    country: 'GB',
    languages: ['en'],
    expertise: ['Maritime'],
    timezone: 'Europe/London',
    is_discoverable: true,
    visible_fields: ['job_title', 'organisation', 'biography', 'country', 'languages', 'expertise'],
    avatar_url: null,
    revision: 3,
    updated_at: null,
    ...overrides,
  };
}

beforeEach(() => {
  if (!('createObjectURL' in URL)) {
    Object.assign(URL, { createObjectURL: () => 'blob:avatar', revokeObjectURL: () => undefined });
  }
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:avatar');
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
});

describe('directory profile editor', () => {
  it('saves per-field directory visibility with timezone private by default', async () => {
    let body: Record<string, unknown> | null = null;
    server.use(
      http.get('/api/me/directory-profile', () => HttpResponse.json(profile())),
      http.patch('/api/me/directory-profile', async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          profile({
            visible_fields: body.visible_fields as DirectoryProfileData['visible_fields'],
          }),
        );
      }),
    );
    const user = userEvent.setup();
    render(<DirectoryProfile />);

    const visibility = within(
      (await screen.findByText('Show in directory results')).closest('fieldset')!,
    );
    expect(visibility.getByRole('checkbox', { name: 'Timezone' })).not.toBeChecked();
    expect(visibility.getByRole('checkbox', { name: 'Organisation' })).toBeChecked();
    expect(screen.getByRole('button', { name: 'Save directory profile' })).toBeDisabled();

    await user.click(visibility.getByRole('checkbox', { name: 'Organisation' }));
    await user.click(visibility.getByRole('checkbox', { name: 'Timezone' }));
    await user.click(screen.getByRole('button', { name: 'Save directory profile' }));

    expect(await screen.findByText('Directory profile saved.')).toBeVisible();
    expect(body).toMatchObject({
      expected_revision: 3,
      timezone: 'Europe/London',
      visible_fields: ['job_title', 'biography', 'country', 'languages', 'expertise', 'timezone'],
    });
    expect(body).not.toHaveProperty('show_timezone');
  });

  it('uploads and removes an avatar while keeping unsaved text edits', async () => {
    let uploadedType: string | null = null;
    server.use(
      http.get('/api/me/directory-profile', () => HttpResponse.json(profile())),
      http.put('/api/me/directory-profile/avatar', async ({ request }) => {
        uploadedType = request.headers.get('content-type');
        await request.arrayBuffer();
        return HttpResponse.json(profile({ avatar_url: AVATAR, revision: 4 }));
      }),
      http.get(`/api/directory/users/${USER_ID}/avatar`, () =>
        HttpResponse.arrayBuffer(new Uint8Array([1, 2, 3]).buffer, {
          headers: { 'Content-Type': 'image/webp' },
        }),
      ),
      http.delete('/api/me/directory-profile/avatar', () =>
        HttpResponse.json(profile({ avatar_url: null, revision: 5 })),
      ),
    );
    const user = userEvent.setup();
    render(<DirectoryProfile />);

    const jobTitle = await screen.findByRole('textbox', { name: 'Job title' });
    await user.clear(jobTitle);
    await user.type(jobTitle, 'Senior analyst');
    const file = new File([new Uint8Array(512)], 'me.png', { type: 'image/png' });
    await user.upload(screen.getByLabelText('Upload avatar image'), file);

    expect(await screen.findByRole('img', { name: /Avatar for/ })).toHaveAttribute(
      'src',
      'blob:avatar',
    );
    expect(uploadedType).toBe('application/octet-stream');
    expect(screen.getByRole('textbox', { name: 'Job title' })).toHaveValue('Senior analyst');

    await user.click(screen.getByRole('button', { name: 'Remove avatar' }));
    await waitFor(() => expect(screen.queryByRole('img')).not.toBeInTheDocument());
    expect(screen.queryByRole('button', { name: 'Remove avatar' })).not.toBeInTheDocument();
  });

  it('rejects oversize or unsupported avatar files before uploading', async () => {
    const upload = vi.fn();
    server.use(
      http.get('/api/me/directory-profile', () => HttpResponse.json(profile())),
      http.put('/api/me/directory-profile/avatar', () => {
        upload();
        return HttpResponse.json(profile());
      }),
    );
    const user = userEvent.setup({ applyAccept: false });
    render(<DirectoryProfile />);
    const picker = await screen.findByLabelText('Upload avatar image');

    await user.upload(picker, new File(['<svg/>'], 'x.svg', { type: 'image/svg+xml' }));
    expect(await screen.findByText('Choose a JPEG, PNG or WebP image.')).toBeVisible();
    const big = new File([new Uint8Array(2 * 1024 * 1024 + 1)], 'big.jpg', { type: 'image/jpeg' });
    await user.upload(picker, big);
    expect(await screen.findByText('Avatar images must be 2 MB or smaller.')).toBeVisible();
    expect(upload).not.toHaveBeenCalled();
  });

  it('shows a retry path when the profile cannot load', async () => {
    let calls = 0;
    server.use(
      http.get('/api/me/directory-profile', () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(
              { error: { code: 'server_error', message: 'Directory unavailable.' } },
              { status: 503 },
            )
          : HttpResponse.json(profile());
      }),
    );
    const user = userEvent.setup();
    render(<DirectoryProfile />);
    expect(await screen.findByText('Directory unavailable.')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByLabelText('Username')).toHaveValue('field_lead');
  });
});
