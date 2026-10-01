/**
 * axe checks on the DEV fixture previews (KAN-61): the Ukraine, economy, figures and report
 * previews compose the real feature components from fixtures, so they cover states the live
 * routes only reach with populated data. See `src/test/axe.ts` for jsdom's limits.
 */
import { screen } from '@testing-library/react';
import { describe, it, vi } from 'vitest';

import { expectNoAxeViolations } from '@/test/axe';
import { mockWebGl2 } from '@/test/env';
import { renderApp } from '@/test/render';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

const PAGE = 30_000;
// The first lazy route a worker loads compiles cold; wait longer than the default for it.
const COLD = { timeout: 25_000 };

describe('fixture previews have no axe violations', () => {
  it(
    'Ukraine',
    async () => {
      mockWebGl2(true);
      renderApp('/dev/ukraine-preview', 'user');
      await screen.findByRole('heading', { level: 1, name: 'Ukraine war' }, COLD);
      await expectNoAxeViolations();
    },
    PAGE,
  );

  it(
    'economy',
    async () => {
      renderApp('/dev/economy-preview', 'user');
      await screen.findByRole('heading', { level: 1, name: 'Economy' });
      await expectNoAxeViolations();
    },
    PAGE,
  );

  it(
    'public figures',
    async () => {
      renderApp('/dev/figures-preview', 'user');
      await screen.findByRole('heading', { level: 1, name: 'Public figures' });
      await expectNoAxeViolations();
    },
    PAGE,
  );

  it(
    'report reader',
    async () => {
      renderApp('/dev/report-preview', 'user');
      await screen.findByRole('heading', { level: 1 }, COLD);
      await expectNoAxeViolations();
    },
    PAGE,
  );
});
