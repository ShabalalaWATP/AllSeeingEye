import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';

import { RequireAuth } from '@/app/router/guards';
import { LoginPage } from '@/features/auth/LoginPage';
import { draftCount, useDraftState } from '@/lib/formDrafts';
import { useAuthStore } from '@/stores/auth';
import { installDialogStub } from '@/test/dialogStub';
import { expectNoAxeViolations } from '@/test/axe';
import { CSRF_VALUE, plainUser, sessionActivity, tokenFor } from '@/test/fixtures';
import { setCsrfCookie } from '@/test/env';
import { server } from '@/test/server';

import { SessionIdleWarning } from './SessionIdleWarning';

installDialogStub();
const NOW = Date.parse('2026-10-09T12:00:00Z');
afterEach(() => vi.useRealTimers());

function signIn(minutes = 180) {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(NOW);
  setCsrfCookie(CSRF_VALUE);
  useAuthStore
    .getState()
    .setSession({ ...tokenFor(plainUser), activity: sessionActivity(NOW, minutes) });
}

it('opens an accessible warning, focuses Stay and closes only after confirmed activity', async () => {
  signIn();
  vi.setSystemTime(NOW + 175 * 60_000);
  const response = sessionActivity(Date.now());
  server.use(http.post('/api/auth/activity', () => HttpResponse.json(response)));
  render(<SessionIdleWarning now={Date.now()} />);
  const dialog = screen.getByRole('alertdialog', {
    name: "You'll be signed out soon for security",
  });
  expect(dialog).toHaveTextContent('Your session ends in 5 minutes');
  expect(screen.getByRole('button', { name: 'Stay signed in' })).toHaveFocus();
  await expectNoAxeViolations(dialog);
  fireEvent.click(screen.getByRole('button', { name: 'Stay signed in' }));
  await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
  expect(useAuthStore.getState().activity?.data).toEqual(response);
});

it('announces only minute changes and gives the minimum timeout a minute before warning again', () => {
  signIn(5);
  const view = render(<SessionIdleWarning now={NOW + 59_999} />);
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  view.rerender(<SessionIdleWarning now={NOW + 60_000} />);
  expect(screen.getByRole('status', { name: 'Session time remaining' })).toHaveTextContent(
    '4 minutes',
  );
  view.rerender(<SessionIdleWarning now={NOW + 89_999} />);
  expect(screen.getByRole('status', { name: 'Session time remaining' })).toHaveTextContent(
    '4 minutes',
  );
});

it('keeps the warning open on heartbeat failure, supports explicit sign-out and prevents dismissal', async () => {
  signIn();
  vi.setSystemTime(NOW + 179 * 60_000);
  server.use(http.post('/api/auth/activity', () => HttpResponse.error()));
  render(<SessionIdleWarning now={Date.now()} />);
  const dialog = screen.getByRole('alertdialog');
  expect(screen.getByRole('status', { name: 'Session time remaining' })).toHaveTextContent(
    '1 minute',
  );
  fireEvent.click(screen.getByRole('button', { name: 'Stay signed in' }));
  expect(await screen.findByText(/Your session has not been extended/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Stay signed in' })).toBeDisabled();
  const cancel = new Event('cancel', { cancelable: true });
  fireEvent(dialog, cancel);
  fireEvent.keyDown(dialog, { key: 'Escape' });
  expect(cancel.defaultPrevented).toBe(true);
  expect(dialog).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
  expect(useAuthStore.getState().status).toBe('anonymous');
  await useAuthStore.getState().pendingLogout;
});

it('expires immediately on resume, clears drafts and preserves the route with the actual duration', async () => {
  signIn(15);
  const draft = renderHook(() => useDraftState('idle-test', 'question', ''));
  act(() => draft.result.current[1]('Unsent research'));
  expect(draftCount()).toBe(1);
  const router = createMemoryRouter(
    [
      { element: <RequireAuth />, children: [{ path: '/work', element: <p>Private work</p> }] },
      { path: '/login', element: <LoginPage /> },
    ],
    { initialEntries: ['/work?scope=personal'] },
  );
  render(<RouterProvider router={router} />);
  act(() => {
    vi.setSystemTime(NOW + 15 * 60_000);
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
  expect(router.state.location.state).toEqual({ from: '/work?scope=personal', idleMinutes: 15 });
  expect(
    await screen.findByText(/You were signed out after 15 minutes without activity/),
  ).toHaveTextContent('in-memory drafts were lost');
  expect(useAuthStore.getState().accessToken).toBeNull();
  expect(draftCount()).toBe(0);
  await useAuthStore.getState().pendingLogout;
});

it('preserves component-local unsaved work while a stale tab verifies a still-live server family', async () => {
  signIn();
  let confirm!: () => void;
  const gate = new Promise<void>((done) => {
    confirm = done;
  });
  server.use(
    http.post('/api/auth/logout', async () => {
      await gate;
      return HttpResponse.json(sessionActivity(Date.now()));
    }),
  );
  const router = createMemoryRouter(
    [
      {
        element: <RequireAuth />,
        children: [
          { path: '/work', element: <input aria-label="Unsaved local work" defaultValue="" /> },
        ],
      },
    ],
    { initialEntries: ['/work'] },
  );
  render(<RouterProvider router={router} />);
  fireEvent.change(screen.getByLabelText('Unsaved local work'), {
    target: { value: 'Still editing' },
  });
  act(() => {
    vi.setSystemTime(NOW + 180 * 60_000);
    document.dispatchEvent(new Event('visibilitychange'));
  });
  expect(screen.getByRole('alertdialog')).toBeInTheDocument();
  expect(screen.getByLabelText('Unsaved local work')).toHaveValue('Still editing');
  await act(async () => {
    confirm();
    await useAuthStore.getState().pendingIdleCheck;
  });
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Unsaved local work')).toHaveValue('Still editing');
  expect(router.state.location.pathname).toBe('/work');
});
