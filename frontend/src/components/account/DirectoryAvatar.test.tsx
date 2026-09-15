import { render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { server } from '@/test/server';

import { DirectoryAvatar } from './DirectoryAvatar';

const URL_PATH = '/api/directory/users/0f0e0d0c-0b0a-4908-8706-050403020100/avatar';

beforeEach(() => {
  if (!('createObjectURL' in URL)) {
    Object.assign(URL, { createObjectURL: () => 'blob:x', revokeObjectURL: () => undefined });
  }
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:person');
});

describe('directory avatar', () => {
  it('shows initials without requesting anything when there is no avatar', () => {
    render(<DirectoryAvatar avatarUrl={null} name="Mina Manager" />);
    expect(screen.getByText('MM')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('renders the authenticated avatar as a blob image and revokes it on unmount', async () => {
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
    server.use(
      http.get(URL_PATH, () =>
        HttpResponse.arrayBuffer(new Uint8Array([1]).buffer, {
          headers: { 'Content-Type': 'image/webp' },
        }),
      ),
    );
    const view = render(
      <DirectoryAvatar avatarUrl={`${URL_PATH}?v=0123456789abcdef`} name="Ada" />,
    );
    expect(await screen.findByRole('img', { name: 'Avatar for Ada' })).toHaveAttribute(
      'src',
      'blob:person',
    );
    view.unmount();
    expect(revoke).toHaveBeenCalledWith('blob:person');
  });

  it('falls back to initials when the avatar is not visible to the viewer', async () => {
    const requested = vi.fn();
    server.use(
      http.get(URL_PATH, () => {
        requested();
        return HttpResponse.json(
          { error: { code: 'not_found', message: 'Not found.' } },
          { status: 404 },
        );
      }),
    );
    render(<DirectoryAvatar avatarUrl={`${URL_PATH}?v=0123456789abcdef`} name="Hidden Person" />);
    await waitFor(() => expect(requested).toHaveBeenCalled());
    expect(screen.getByText('HP')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });
});
