/**
 * axe checks on representative signed-in pages inside the real shell (KAN-61): the globe and
 * an open map tool, research, the team workspace, a saved report and administration users.
 * Queries use roles and names only, so the pages can be restructured without editing this
 * file. See `src/test/axe.ts` for the rules jsdom cannot evaluate.
 */
import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, it, vi } from 'vitest';

import { expectNoAxeViolations } from '@/test/axe';
import { installDialogStub } from '@/test/dialogStub';
import { mockWebGl2 } from '@/test/env';
import { roster } from '@/test/fixtures.teams';
import { reportSummary } from '@/test/fixtures.reports';
import { openMapTool } from '@/test/mapTools';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));
vi.mock('@/lib/sse', () => import('@/test/fakeStream'));

installDialogStub();

// Lazy routes load cold in the first test of a worker; allow for it.
const PAGE = 30_000;
// The first lazy route a worker loads compiles cold; wait longer than the default for it.
const COLD = { timeout: 25_000 };

describe('signed-in pages have no axe violations', () => {
  it(
    'globe with its map controls',
    async () => {
      mockWebGl2(true);
      const { user } = renderApp('/', 'user');
      await screen.findByRole('heading', { level: 1 }, COLD);
      await expectNoAxeViolations();
      await openMapTool(user, 'Draw on map');
      await screen.findByRole('region', { name: 'Draw on map' });
      await expectNoAxeViolations();
    },
    PAGE,
  );

  it(
    'research form',
    async () => {
      renderApp('/research', 'user');
      await screen.findByRole('heading', { level: 1, name: 'Research' });
      await screen.findByRole('textbox', { name: /question/i });
      await expectNoAxeViolations();
    },
    PAGE,
  );

  it(
    'team workspace',
    async () => {
      server.use(
        http.get('/api/teams', () => HttpResponse.json({ items: [roster.team] })),
        http.get('/api/teams/:id', () => HttpResponse.json(roster)),
      );
      renderApp('/teams', 'user');
      await screen.findByRole('heading', { level: 1, name: 'Teams' });
      await screen.findByRole('table', { name: 'Team members' });
      await expectNoAxeViolations();
    },
    PAGE,
  );

  it(
    'report reader',
    async () => {
      renderApp(`/reports/${reportSummary.id}`, 'user');
      await screen.findByRole('heading', { level: 1, name: reportSummary.title });
      await expectNoAxeViolations();
    },
    PAGE,
  );

  it(
    'administration users',
    async () => {
      renderApp('/admin/users', 'admin');
      await screen.findByRole('table');
      await expectNoAxeViolations();
    },
    PAGE,
  );
});
