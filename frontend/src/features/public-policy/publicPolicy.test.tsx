import { act, screen, waitFor, within } from '@testing-library/react';
import axe from 'axe-core';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { expectNoAxeViolations } from '@/test/axe';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { useAuthStore } from '@/stores/auth';

import { storageDeclaration } from './content';

vi.mock('virtual:policy-approval', () => ({ default: false }));
// Exercise incomplete installations independently of the approved shipped notice.
vi.mock('./privacy.json', async (original) => {
  const { default: notice } = await original<{
    default: { operator: Record<string, string | null> };
  }>();
  return {
    default: {
      ...notice,
      operator: { ...notice.operator, jurisdiction: null, internationalTransfers: null },
    },
  };
});

describe('public policy pages', () => {
  it.each([
    ['/privacy', 'Privacy and storage'],
    ['/attributions', 'Source attributions'],
    ['/privacy/requests', 'Personal-data requests'],
    ['/accessibility', 'Accessibility'],
    ['/terms', 'Terms'],
    ['/acceptable-use', 'Acceptable Use Policy'],
    ['/business', 'Business details'],
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
    expect(screen.getAllByText(/Not yet confirmed by the operator/).length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: 'Your right to object' })).toBeInTheDocument();
    expect(screen.getByText(/not a complete approved retention policy/)).toBeInTheDocument();
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

  it('shows the structured terms while keeping outstanding decisions and approval explicit', async () => {
    const { router } = renderApp('/terms', 'anonymous');
    await screen.findByRole('heading', { level: 1, name: 'Terms' });
    expect(screen.getByLabelText('Draft notice')).toHaveTextContent('Publication is blocked');
    expect(screen.getByText(/Version of/)).toHaveTextContent('Version of 18 October 2026');
    for (const name of [
      'The service',
      'Who may use it',
      'Your account',
      'AI output',
      'Availability',
      'Liability',
      'Governing law',
      'How changes are notified',
    ])
      expect(screen.getByRole('heading', { level: 2, name })).toBeInTheDocument();
    expect(screen.getByText(/You must be 18 or over/)).toBeInTheDocument();
    expect(
      screen.getByText(/These access rules do not grant a software redistribution licence/),
    ).toBeInTheDocument();
    const law = screen.getByRole('region', { name: 'Governing law' });
    expect(law).toHaveTextContent(/Decision needed:.*England and Wales.*This blocks publication/);
    await act(() => router.navigate('/business'));
    await screen.findByRole('heading', { level: 1, name: 'Business details' });
    expect(screen.getByText('Controller identity')).toBeInTheDocument();
    expect(screen.getByText('Alex Orr')).toBeInTheDocument();
    expect(screen.getByText('alexorr@yahoo.co.uk')).toBeInTheDocument();
    expect(screen.getByText('Geographic business address')).toBeInTheDocument();
    // The mocked jurisdiction and the unconfirmed business address.
    expect(screen.getAllByText(/Not yet confirmed by the operator/)).toHaveLength(2);
  });

  it('lists every prohibited use, the misuse contact and the consequences', async () => {
    renderApp('/acceptable-use', 'anonymous');
    await screen.findByRole('heading', { level: 1, name: 'Acceptable Use Policy' });
    const prohibited = screen.getByRole('region', { name: 'You must not' });
    for (const use of [
      /target, profile, locate or monitor private individuals/,
      /harass/,
      /Computer Misuse Act 1990.*export controls or sanctions/,
      /circumvent a source's terms.*redistribute licensed data/,
      /sole basis for decisions affecting individuals' rights/,
    ])
      expect(within(prohibited).getByText(use)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'How to report misuse' })).toHaveTextContent(
      'alexorr@yahoo.co.uk',
    );
    expect(
      screen.getByRole('region', { name: 'What happens to accounts that break this policy' }),
    ).toHaveTextContent(/deactivate an account.*Decision needed/);
    expect(within(screen.getByRole('main')).getByRole('link', { name: 'Terms' })).toHaveAttribute(
      'href',
      '/terms',
    );
  });

  it('publishes an honest accessibility statement with dated review and pending decisions', async () => {
    renderApp('/accessibility', 'anonymous');
    await screen.findByRole('heading', { level: 1, name: 'Accessibility' });
    expect(screen.getByRole('region', { name: 'Technical standard' })).toHaveTextContent(
      'WCAG) version 2.2 at level AA',
    );
    expect(screen.getByRole('region', { name: 'Compliance status' })).toHaveTextContent(
      'partially compliant',
    );
    expect(screen.queryByText(/fully compliant/)).not.toBeInTheDocument();
    const limits = screen.getByRole('region', { name: 'Known limitations and workarounds' });
    for (const limit of [/3D globe/, /no captions/, /Third-party embeds/])
      expect(within(limits).getByText(limit)).toBeInTheDocument();
    const feedback = screen.getByRole('region', { name: 'Reporting accessibility problems' });
    expect(feedback).toHaveTextContent('alexorr@yahoo.co.uk');
    expect(feedback).toHaveTextContent(/Decision needed: Expected response time/);
    expect(screen.getByRole('region', { name: 'Enforcement and complaints' })).toHaveTextContent(
      'Decision needed',
    );
    expect(screen.getByRole('region', { name: 'How this service was tested' })).toHaveTextContent(
      /axe-core.*No complete manual keyboard or screen reader pass/,
    );
    expect(screen.getByRole('region', { name: 'Preparation of this statement' })).toHaveTextContent(
      'Last reviewed on 18 October 2026. The next review is due by 18 April 2027.',
    );
  });

  it.each(['/accessibility', '/terms', '/acceptable-use'])(
    'renders %s with no detectable accessibility violations',
    async (path) => {
      const { container } = renderApp(path, 'anonymous');
      await screen.findByRole('heading', { level: 1 });
      await expectNoAxeViolations(container);
    },
  );

  it('names the operator and links every policy from the shared footer', async () => {
    renderApp('/privacy', 'anonymous');
    await screen.findByRole('heading', { level: 1, name: 'Privacy and storage' });
    const footer = screen.getByRole('contentinfo');
    expect(within(footer).getByRole('link', { name: 'Acceptable use' })).toHaveAttribute(
      'href',
      '/acceptable-use',
    );
    expect(footer).toHaveTextContent(
      'Operated by Alex Orr · alexorr@yahoo.co.uk · Business address awaiting the operator’s decision',
    );
    // The header repeats the links without repeating the operator line.
    expect(screen.getAllByText(/Operated by Alex Orr/)).toHaveLength(1);
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
