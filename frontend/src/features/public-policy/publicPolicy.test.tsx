import { act, screen, waitFor, within } from '@testing-library/react';
import axe from 'axe-core';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { useAuthStore } from '@/stores/auth';

import { storageDeclaration } from './content';

vi.mock('virtual:policy-approval', () => ({ default: false }));

describe('public policy pages', () => {
  it.each([
    ['/privacy', 'Privacy and storage'],
    ['/attributions', 'Source attributions'],
    ['/privacy/requests', 'Personal-data requests'],
  ])('renders %s without a session or a third-party request', async (path, title) => {
    const bootstrap = vi.spyOn(useAuthStore.getState(), 'bootstrap');
    const requests: string[] = [];
    const record = ({ request }: { request: Request }) => {
      requests.push(request.url);
    };
    server.events.on('request:start', record);
    try {
      renderApp(path, 'unknown');
      await screen.findByRole('heading', { level: 1, name: title });
      await waitFor(() => {
        expect(document.title).toBe(`${title} · The All Seeing Eye`);
      });
      expect(bootstrap).not.toHaveBeenCalled();
      expect(
        document.querySelectorAll('iframe,video,script[src^="http"],img[src^="http"]'),
      ).toHaveLength(0);
      expect(
        requests.every(
          (url) =>
            new URL(url).origin === window.location.origin && new URL(url).pathname === '/api/site',
        ),
      ).toBe(true);
    } finally {
      server.events.removeListener('request:start', record);
    }
  });

  it('shows the live retention value and every declared browser key, while keeping draft decisions explicit', async () => {
    let credentials: RequestCredentials | undefined;
    server.use(
      http.get('/api/site', ({ request }) => {
        credentials = request.credentials;
        expect(request.headers.has('authorization')).toBe(false);
        return HttpResponse.json({ enterprise_enquiry_retention_days: 90 });
      }),
    );
    renderApp('/privacy', 'anonymous');
    await screen.findByText(/configured for 90 days/);
    expect(credentials).toBe('omit');
    expect(screen.getByLabelText('Draft notice')).toHaveTextContent('Publication is blocked');
    for (const declaration of storageDeclaration)
      expect(screen.getByText(declaration.name)).toBeInTheDocument();
    expect(screen.getByText('Controller identity')).toBeInTheDocument();
    expect(screen.getAllByText(/Not yet confirmed by the operator/).length).toBeGreaterThan(5);
  });

  it.each([HttpResponse.json({ enterprise_enquiry_retention_days: 99999 }), HttpResponse.error()])(
    'never presents a fallback as the live retention setting',
    async (response) => {
      server.use(http.get('/api/site', () => response));
      renderApp('/privacy', 'anonymous');
      await screen.findByText(/current retention setting could not be loaded/);
      expect(screen.queryByText(/configured for 365 days/)).not.toBeInTheDocument();
    },
  );

  it('links the approved request procedure without describing it as complete erasure', async () => {
    renderApp('/privacy/requests', 'anonymous');
    const email = await screen.findByRole('link', { name: 'alexorr@yahoo.co.uk' });
    expect(email).toHaveAttribute('href', 'mailto:alexorr@yahoo.co.uk');
    expect(
      screen.getByText(/There is no complete account-wide export or erasure action/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Shared team work is preserved/)).toBeInTheDocument();
  });

  it('keeps public links keyboard reachable and provides structural accessibility', async () => {
    const { user, container, router } = renderApp('/privacy/requests', 'anonymous');
    await screen.findByRole('heading', { name: 'Personal-data requests' });
    await user.tab();
    expect(screen.getByRole('link', { name: 'Skip to content' })).toHaveFocus();
    const nav = screen.getAllByRole('navigation', { name: 'Privacy and source information' })[0]!;
    await user.click(within(nav).getByRole('link', { name: 'Privacy and storage' }));
    await screen.findByRole('heading', { name: 'Privacy and storage' });
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Privacy and storage' })).toHaveFocus();
    });
    expect(
      (await axe.run(container, { rules: { 'color-contrast': { enabled: false } } })).violations,
    ).toEqual([]);
    await act(() => router.navigate('/attributions'));
    await screen.findByRole('heading', { name: 'Source attributions' });
    expect(screen.getByText(/A credit is not permission/)).toBeInTheDocument();
    expect(screen.getByText(/superset of the sources/)).toBeInTheDocument();
  });
});
