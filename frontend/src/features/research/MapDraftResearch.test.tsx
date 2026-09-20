import { act, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { beforeEach, expect, it } from 'vitest';
import { applySession } from '@/test/render';
import { researchArea } from '@/test/areaResearchPanel';
import { defaultProfile } from '@/test/handlers.profile';
import { prepareAreaResearchHandoff } from '@/lib/areaResearchDraft';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { MapDraftResearch } from './MapDraftResearch';

beforeEach(() => applySession('user'));
it('fails closed when a map handoff is unavailable', () => {
  render(
    <MemoryRouter>
      <MapDraftResearch />
    </MemoryRouter>,
  );
  expect(screen.getByText(/draft is unavailable/)).toBeVisible();
  expect(screen.getByRole('link', { name: 'Return to map' })).toHaveAttribute('href', '/');
  expect(screen.queryByLabelText('Question (optional)')).not.toBeInTheDocument();
});
it('shows the exact handoff and removes the form immediately after access invalidation', () => {
  prepareAreaResearchHandoff(researchArea, undefined, defaultProfile);
  render(
    <MemoryRouter>
      <MapDraftResearch />
    </MemoryRouter>,
  );
  expect(screen.getByText(/Coordinates have not been widened/)).toBeVisible();
  expect(
    screen.queryByRole('button', { name: 'Continue on research page' }),
  ).not.toBeInTheDocument();
  act(() => invalidateWorkspaceAccess());
  expect(screen.getByText(/draft is unavailable/)).toBeVisible();
  expect(screen.queryByLabelText('Question (optional)')).not.toBeInTheDocument();
});
