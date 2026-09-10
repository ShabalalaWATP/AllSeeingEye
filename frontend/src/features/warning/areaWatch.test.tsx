import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { WatchAreaButton } from '@/components/maps/WatchAreaButton';
import { prepareAreaWatch, readAreaWatchDraft } from '@/lib/areaWatchDraft';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor, indicator } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import WarningPage from './WarningPage';

const area = {
  source: 'rectangle' as const,
  bounds: { west: 170, south: -10, east: -170, north: 10 },
};
it('hands off a map area, edits its bounds and creates nothing until Add indicator', async () => {
  const requests: unknown[] = [];
  server.use(
    http.post('/api/warning/indicators', async ({ request }) => {
      requests.push(await request.json());
      return HttpResponse.json(indicator, { status: 201 });
    }),
  );
  useAuthStore.getState().setSession(tokenFor(plainUser));
  const router = createMemoryRouter([
    { path: '/', element: <WatchAreaButton area={area} /> },
    { path: '/warning', element: <WarningPage /> },
  ]);
  render(<RouterProvider router={router} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Watch this area' }));
  expect(router.state.location.pathname).toBe('/warning');
  expect(router.state.location.search).toBe('');
  const form = await screen.findByRole('form', { name: 'New indicator' });
  expect(within(form).getByLabelText('West bound')).toHaveValue(170);
  expect(within(form).getByLabelText('East bound')).toHaveValue(-170);
  expect(within(form).queryByLabelText('Nations')).not.toBeInTheDocument();
  expect(within(form).getByLabelText('Report when it fires')).toHaveValue('');
  expect(requests).toHaveLength(0);
  await user.type(within(form).getByLabelText('Indicator name'), 'Pacific watch');
  fireEvent.change(within(form).getByLabelText('West bound'), { target: { value: '175' } });
  await user.click(within(form).getByRole('button', { name: 'Add indicator' }));
  await waitFor(() => expect(requests).toHaveLength(1));
  expect(requests[0]).toMatchObject({
    name: 'Pacific watch',
    bbox: [175, -10, -170, 10],
    countries: [],
    report_template: null,
  });
  await waitFor(() => expect(readAreaWatchDraft()).toBeNull());
});
it('requires valid area coordinates and keeps nation and area criteria exclusive', async () => {
  let submitted: unknown;
  server.use(
    http.post('/api/warning/indicators', async ({ request }) => {
      submitted = await request.json();
      return HttpResponse.json(indicator, { status: 201 });
    }),
  );
  const { user } = renderApp('/warning', 'user');
  const form = await screen.findByRole('form', { name: 'New indicator' });
  await user.type(within(form).getByLabelText('Indicator name'), 'Scope check');
  await user.type(within(form).getByLabelText('Nations'), 'GB');
  await user.selectOptions(within(form).getByLabelText('Location scope'), 'area');
  const submit = within(form).getByRole('button', { name: 'Add indicator' });
  expect(submit).toBeDisabled();
  fireEvent.submit(form);
  expect(submitted).toBeUndefined();
  for (const [label, value] of Object.entries({ West: '0', East: '2', South: '50', North: '49' }))
    fireEvent.change(within(form).getByLabelText(`${label} bound`), { target: { value } });
  expect(submit).toBeDisabled();
  fireEvent.change(within(form).getByLabelText('North bound'), { target: { value: '51' } });
  expect(submit).toBeEnabled();
  await user.selectOptions(within(form).getByLabelText('Location scope'), 'nations');
  await user.click(submit);
  await waitFor(() => expect(submitted).toMatchObject({ countries: ['GB'] }));
  expect(submitted).not.toHaveProperty('bbox');
});
it('discards drafts explicitly and removes both draft and edited form on access invalidation', async () => {
  useAuthStore.getState().setSession(tokenFor(plainUser));
  prepareAreaWatch(area);
  const { user } = renderApp('/warning', 'user');
  let form = await screen.findByRole('form', { name: 'New indicator' });
  await user.type(within(form).getByLabelText('Indicator name'), 'Private location');
  act(() => invalidateWorkspaceAccess());
  form = screen.getByRole('form', { name: 'New indicator' });
  expect(within(form).getByLabelText('Indicator name')).toHaveValue('');
  expect(within(form).queryByLabelText('West bound')).not.toBeInTheDocument();
  act(() => prepareAreaWatch({ ...area, source: 'sketch-envelope' }));
  expect(screen.getByText(/approximate bounding rectangle includes areas outside/)).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Discard map draft' }));
  expect(readAreaWatchDraft()).toBeNull();
});
