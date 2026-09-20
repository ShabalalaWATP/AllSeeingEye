import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { expect, it } from 'vitest';
import { aoi } from '@/test/fixtures.direction';
import { applySession } from '@/test/render';
import { readAreaResearchHandoff } from '@/lib/areaResearchDraft';
import { researchAreaGeometry } from '@/lib/map/researchAreaGeometry';
import { rectangleArea } from '@/lib/map/areaGeometry';
import { ResearchAreaButton } from './ResearchAreaButton';

it('reuses an exact saved area through the private research handoff', async () => {
  applySession('user');
  const geometry = researchAreaGeometry('polygon', [
    [0, 0],
    [2, 0],
    [0, 2],
  ]);
  const router = createMemoryRouter([
    {
      path: '/',
      element: (
        <ResearchAreaButton
          area={{
            ...aoi,
            kind: 'geometry',
            bbox: null,
            research_area: { geometry: { ...geometry }, sha256: 'a'.repeat(64) },
          }}
        />
      ),
    },
    { path: '/research', element: <div>Research draft</div> },
  ]);
  render(<RouterProvider router={router} />);
  await userEvent.setup().click(screen.getByRole('button', { name: 'Research area' }));
  expect(router.state.location.pathname).toBe('/research');
  expect(router.state.location.search).toBe('?map_draft=1');
  expect(readAreaResearchHandoff()?.area).toEqual(geometry);
});

it('keeps the shorter dateline boundary when reusing a legacy rectangle', async () => {
  applySession('user');
  const router = createMemoryRouter([
    { path: '/', element: <ResearchAreaButton area={{ ...aoi, bbox: [170, -10, -170, 10] }} /> },
    { path: '/research', element: <div>Research draft</div> },
  ]);
  render(<RouterProvider router={router} />);
  await userEvent.setup().click(screen.getByRole('button', { name: 'Research area' }));
  expect(router.state.location.pathname).toBe('/research');
  expect(readAreaResearchHandoff()?.area).toEqual(
    rectangleArea({ west: 170, east: -170, south: -10, north: 10 }),
  );
});
