import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it } from 'vitest';

import { expectNoAxeViolations } from '@/test/axe';
import { mockMatchMedia } from '@/test/env';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { resetSiteFacts } from '@/lib/useSiteFacts';
import { MOTION_STORAGE_KEY } from '@/components/brand/localMotionPause';

import { EXAMPLE_QUESTION } from './content/research';
import { MAP_TOOLS, STORY_LAYERS } from './content/observe';

/** A mouse or trackpad: hover-capable and fine, with no reduced-motion request. */
function finePointer() {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: query === '(hover: hover) and (pointer: fine)',
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

function siteFacts(enabled: boolean) {
  server.use(http.get('/api/site', () => HttpResponse.json({ product_page_enabled: enabled })));
}

describe('public product page', () => {
  afterEach(() => resetSiteFacts());

  it('tells the whole story without signing in when the installation enables it', async () => {
    siteFacts(true);
    renderApp('/enterprise', 'anonymous');
    expect(
      await screen.findByRole('heading', { level: 1, name: /The All Seeing Eye/ }),
    ).toBeInTheDocument();
    for (const name of [
      'One picture of a noisy world.',
      'Cut the picture down to what matters.',
      'Hundreds of sources, organised by topic.',
      'Start with a question, not a search box.',
      'Evidence with a receipt, and gaps you can see.',
      'Judgements you can trace, challenge and defend.',
      'An assessment is the start of the work, not the end.',
      'Specialist workspaces for specialist questions.',
      'Your server. Your model. Your rules.',
      'One server you run. Your database stays on it.',
      'Bring The All Seeing Eye inside your organisation.',
    ]) {
      expect(screen.getByRole('heading', { level: 2, name })).toBeInTheDocument();
    }
    // The title is set in an effect, which can land after the headings on a busy runner.
    await waitFor(() => expect(document.title).toMatch(/Self-hosted open-source intelligence/));
    const layers = screen.getByRole('region', { name: 'Observe' });
    for (const layer of STORY_LAYERS)
      expect(within(layers).getByText(layer.label)).toBeInTheDocument();
    expect(document.querySelector('.hero-eye [data-testid="evil-eye"]')).not.toBeNull();
    const tools = screen.getByRole('region', { name: 'Filters and map tools' });
    expect(tools).toHaveAttribute('id', 'tools');
    for (const tool of MAP_TOOLS)
      expect(
        within(tools).getByRole('heading', { level: 3, name: tool.label }),
      ).toBeInTheDocument();
    const hero = screen.getByRole('region', { name: 'The All Seeing Eye' });
    expect(within(hero).getByRole('link', { name: 'Talk to us' })).toHaveAttribute(
      'href',
      '/enterprise#contact',
    );
    expect(within(hero).getByRole('link', { name: 'See how it works' })).toHaveAttribute(
      'href',
      '#observe',
    );
    expect(document.getElementById('contact')).not.toBeNull();
    expect(document.getElementById('observe')).not.toBeNull();
    const contact = screen.getByRole('region', { name: 'Talk to us' });
    expect(within(contact).getByRole('link', { name: 'Request access' })).toHaveAttribute(
      'href',
      '/request-account',
    );
    for (const [name, href] of [
      ['Accessibility', '/accessibility'],
      ['Terms', '/terms'],
      ['Business details', '/business'],
    ] as const) {
      expect(screen.getByRole('link', { name })).toHaveAttribute('href', href);
    }
  });

  it('is not found when the installation has not enabled it', async () => {
    siteFacts(false);
    renderApp('/enterprise', 'anonymous');
    expect(await screen.findByRole('heading', { name: /not found/i })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { level: 1, name: /The All Seeing Eye/ })).toBeNull();
  });

  it('stays hidden when the site facts cannot be fetched', async () => {
    server.use(http.get('/api/site', () => HttpResponse.json({}, { status: 500 })));
    renderApp('/enterprise', 'anonymous');
    expect(await screen.findByRole('heading', { name: /not found/i })).toBeInTheDocument();
  });

  it('shows every scene in its final state when motion is reduced', async () => {
    mockMatchMedia(true);
    siteFacts(true);
    renderApp('/enterprise', 'anonymous');
    await screen.findByRole('heading', { level: 1, name: /The All Seeing Eye/ });
    const story = document.querySelector('.product-story');
    expect(story).toHaveAttribute('data-motion', 'still');
    expect(document.querySelectorAll('[data-mode="pinned"]')).toHaveLength(0);
    expect(document.querySelectorAll('.story-reveal[data-shown="false"]')).toHaveLength(0);
    expect(screen.getAllByText(EXAMPLE_QUESTION).length).toBeGreaterThan(0);
    const eye = document.querySelector('.hero-eye [data-testid="evil-eye"]');
    expect(eye).toHaveAttribute('data-flame-speed', '0');
    expect(eye).toHaveAttribute('data-pupil-follow', '0');
  });

  it('lets the hero pupil follow a fine pointer only while the story moves', async () => {
    finePointer();
    siteFacts(true);
    const moving = renderApp('/enterprise', 'anonymous');
    await screen.findByRole('heading', { level: 1, name: /The All Seeing Eye/ });
    const eye = () => document.querySelector('.hero-eye [data-testid="evil-eye"]');
    expect(eye()).toHaveAttribute('data-pupil-follow', '1');
    moving.unmount();

    localStorage.setItem(MOTION_STORAGE_KEY, 'paused');
    renderApp('/enterprise', 'anonymous');
    await screen.findByRole('heading', { level: 1, name: /The All Seeing Eye/ });
    expect(document.querySelector('.product-story')).toHaveAttribute('data-motion', 'still');
    expect(eye()).toHaveAttribute('data-pupil-follow', '0');
  });

  it('keeps the pupil still on touch screens', async () => {
    siteFacts(true);
    renderApp('/enterprise', 'anonymous');
    await screen.findByRole('heading', { level: 1, name: /The All Seeing Eye/ });
    expect(document.querySelector('.product-story')).toHaveAttribute('data-motion', 'moving');
    expect(document.querySelector('.hero-eye [data-testid="evil-eye"]')).toHaveAttribute(
      'data-pupil-follow',
      '0',
    );
  });

  it('has no detectable accessibility violations', async () => {
    siteFacts(true);
    renderApp('/enterprise', 'anonymous');
    await screen.findByRole('heading', { level: 1, name: /The All Seeing Eye/ });
    await waitFor(() => expect(document.querySelector('.product-story')).not.toBeNull());
    await expectNoAxeViolations();
  });
});
