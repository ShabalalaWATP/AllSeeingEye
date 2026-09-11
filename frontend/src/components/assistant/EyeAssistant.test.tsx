import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';
import { applySession } from '@/test/render';
import { server } from '@/test/server';
import { registerAssistantMapContext, clearAssistantMapFocus } from '@/lib/assistantMapContext';
import type { AssistantRequest } from '@/lib/api/assistant';
import { useEventsStore } from '@/stores/events';
import { EyeAssistant } from './EyeAssistant';
import { eyeAnswer } from './assistantFixture';
import { clampAssistantPosition } from './useAssistantPosition';

let releaseMap: () => void = () => undefined;
afterEach(() => {
  releaseMap();
  clearAssistantMapFocus();
});
function mount(session: 'user' | 'anonymous' = 'user') {
  applySession(session);
  render(
    <MemoryRouter>
      <EyeAssistant />
    </MemoryRouter>,
  );
  return userEvent.setup();
}

it('only renders for authenticated accounts and uses the original captured eye without WebGL', () => {
  mount('anonymous');
  expect(screen.queryByRole('button', { name: 'Open Eye assistant' })).not.toBeInTheDocument();
  act(() => applySession('user'));
  expect(screen.getByRole('button', { name: 'Open Eye assistant' })).toBeVisible();
  expect(document.querySelector('.eye-launcher img')).toHaveAttribute('src', '/brand/eye-512.png');
  expect(document.querySelector('canvas')).toBeNull();
});

it('opens a compact non-modal panel and returns focus when Escape closes it', async () => {
  const user = mount();
  const launcher = screen.getByRole('button', { name: 'Open Eye assistant' });
  await user.click(launcher);
  const panel = screen.getByRole('dialog', { name: 'Eye assistant' });
  expect(panel).toHaveAttribute('aria-modal', 'false');
  expect(parseInt(panel.style.width)).toBeLessThanOrEqual(390);
  expect(screen.getByLabelText('Ask the Eye')).toHaveFocus();
  await user.keyboard('{Escape}');
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(launcher).toHaveFocus();
});

it('distinguishes pointer dragging from clicking and supports keyboard movement and reset', async () => {
  const user = mount();
  const launcher = screen.getByRole('button', { name: 'Open Eye assistant' });
  const initial = launcher.style.left;
  fireEvent(
    launcher,
    new MouseEvent('pointerdown', { bubbles: true, button: 0, clientX: 100, clientY: 100 }),
  );
  fireEvent(
    launcher,
    new MouseEvent('pointermove', { bubbles: true, button: 0, clientX: 40, clientY: 40 }),
  );
  fireEvent(
    launcher,
    new MouseEvent('pointerup', { bubbles: true, button: 0, clientX: 40, clientY: 40 }),
  );
  fireEvent.click(launcher);
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(launcher.style.left).not.toBe(initial);
  launcher.focus();
  const previous = parseInt(launcher.style.left);
  await user.keyboard('{ArrowLeft}');
  expect(parseInt(launcher.style.left)).toBe(previous - 16);
  await user.keyboard('{Home}');
  expect(launcher.style.left).toBe(initial);
  await user.click(launcher);
  expect(screen.getByRole('dialog')).toBeVisible();
  expect(clampAssistantPosition({ x: 9000, y: -200 }, { width: 320, height: 260 })).toEqual({
    x: 232,
    y: 12,
  });
});

it('searches all retained sources regardless of display toggles and renders cited coverage', async () => {
  let body: AssistantRequest | undefined;
  server.use(
    http.post('/api/assistant/answer', async ({ request }) => {
      body = (await request.json()) as AssistantRequest;
      return HttpResponse.json(eyeAnswer);
    }),
  );
  const user = mount();
  useEventsStore.setState({ hidden: ['maritime', 'aviation'], country: 'GB', windowHours: 1 });
  await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
  await user.type(screen.getByLabelText('Ask the Eye'), 'Where are the ships?');
  await user.click(screen.getByRole('button', { name: 'Ask Eye' }));
  expect(await screen.findByText('Two recent vessel observations are available.')).toBeVisible();
  expect(body).toEqual({ question: 'Where are the ships?', prior_questions: [], scope: 'global' });
  expect(screen.getByRole('link', { name: 'E1 · Example vessel position' })).toHaveAttribute(
    'href',
    'https://example.org/vessel',
  );
  await user.click(screen.getByText('Sources and coverage'));
  expect(screen.getByText(/The answer uses a bounded sample/)).toBeVisible();
  expect(screen.getByText(/Publication time unknown/)).toBeVisible();
  expect(screen.getByText(/AIS coverage is incomplete/)).toBeVisible();
});

it('captures current antimeridian bounds and selected catalogue identity only when explicitly requested', async () => {
  const bodies: AssistantRequest[] = [];
  server.use(
    http.post('/api/assistant/answer', async ({ request }) => {
      bodies.push((await request.json()) as AssistantRequest);
      return HttpResponse.json(eyeAnswer);
    }),
  );
  releaseMap = registerAssistantMapContext(() => ({
    bounds: [170, -20, -170, 20],
    selected: { kind: 'camera', id: 'camera-7', title: 'Harbour camera' },
  }));
  const user = mount();
  await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
  await user.selectOptions(screen.getByLabelText('Eye search scope'), 'viewport');
  await user.type(screen.getByLabelText('Ask the Eye'), 'What is here?{Enter}');
  await screen.findByText('Two recent vessel observations are available.');
  expect(bodies[0]).toMatchObject({
    scope: 'viewport',
    bbox: { west: 170, south: -20, east: -170, north: 20 },
  });
  expect(bodies[0]).not.toHaveProperty('selected');
  await user.selectOptions(screen.getByLabelText('Eye search scope'), 'selected');
  await user.type(screen.getByLabelText('Ask the Eye'), 'Explain this camera.{Enter}');
  await waitFor(() => expect(bodies).toHaveLength(2));
  expect(bodies[1]).toMatchObject({
    scope: 'selected',
    selected: { kind: 'camera', id: 'camera-7' },
    prior_questions: ['What is here?'],
  });
  expect(bodies[1]).not.toHaveProperty('bbox');
});

it('does not silently widen a selected-item question when the map context disappears', async () => {
  let calls = 0;
  server.use(
    http.post('/api/assistant/answer', () => {
      calls++;
      return HttpResponse.json(eyeAnswer);
    }),
  );
  releaseMap = registerAssistantMapContext(() => ({
    bounds: null,
    selected: { kind: 'event', id: 'one', title: 'Selected event' },
  }));
  const user = mount();
  await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
  await user.selectOptions(screen.getByLabelText('Eye search scope'), 'selected');
  act(() => releaseMap());
  await user.type(screen.getByLabelText('Ask the Eye'), 'Explain this.{Enter}');
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Select an event, camera or infrastructure item',
  );
  expect(calls).toBe(0);
});

it('locates a cited source through the existing map engine bridge', async () => {
  const focus = vi.fn();
  releaseMap = registerAssistantMapContext(
    () => ({ bounds: [-180, -90, 180, 90], selected: null }),
    focus,
  );
  server.use(http.post('/api/assistant/answer', () => HttpResponse.json(eyeAnswer)));
  const user = mount();
  await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
  await user.type(screen.getByLabelText('Ask the Eye'), 'Locate a vessel.{Enter}');
  await screen.findByText('Two recent vessel observations are available.');
  await user.click(screen.getByText('Sources and coverage'));
  await user.click(screen.getByRole('button', { name: 'Centre map here' }));
  expect(focus).toHaveBeenCalledWith({ lon: 179.5, lat: 42 });
});
