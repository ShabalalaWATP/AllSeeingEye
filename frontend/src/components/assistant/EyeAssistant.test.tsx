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
import { answerWithReferences } from './EyeAnswer';
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

it('only renders for authenticated accounts and animates the original eye transparently', () => {
  mount('anonymous');
  expect(screen.queryByRole('button', { name: 'Open Eye assistant' })).not.toBeInTheDocument();
  act(() => applySession('user'));
  expect(screen.getByRole('button', { name: 'Open Eye assistant' })).toBeVisible();
  expect(screen.getByTestId('evil-eye')).toHaveAttribute('data-transparent', 'true');
  expect(screen.getByTestId('evil-eye')).toHaveAttribute('data-max-fps', '24');
  expect(screen.getByTestId('evil-eye')).toHaveAttribute('data-pupil-follow', '1');
  expect(screen.getByText('ASK EYE')).toBeVisible();
});

it('opens a compact non-modal panel and returns focus when Escape closes it', async () => {
  const user = mount();
  const launcher = screen.getByRole('button', { name: 'Open Eye assistant' });
  await user.click(launcher);
  const panel = screen.getByRole('dialog', { name: 'Eye assistant' });
  expect(panel).toHaveAttribute('aria-modal', 'false');
  expect(parseInt(panel.style.width)).toBeLessThanOrEqual(420);
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
    x: 172,
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
  await user.click(
    screen.getByRole('button', { name: 'View evidence E1: Example vessel position' }),
  );
  expect(screen.getByRole('link', { name: 'Open original' })).toHaveAttribute(
    'href',
    'https://example.org/vessel',
  );
  expect(screen.getByText(/The answer uses a bounded sample/)).toBeVisible();
  expect(screen.getByText(/Publication time unknown/)).toBeVisible();
  expect(screen.getByText(/AIS coverage is incomplete/)).toBeVisible();
  expect(screen.queryByText('fixture-model')).not.toBeInTheDocument();
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

it('applies an explicit publication window and carries interpreted country and dates to Research', async () => {
  let body: AssistantRequest | undefined;
  server.use(
    http.post('/api/assistant/answer', async ({ request }) => {
      body = (await request.json()) as AssistantRequest;
      return HttpResponse.json({
        ...eyeAnswer,
        interpretation: {
          ...eyeAnswer.interpretation,
          topics: ['conflict'],
          countries: ['GB'],
          since: '2026-09-11T00:00:00Z',
          until: '2026-09-12T00:00:00Z',
          time_basis: 'publication',
          notes: ['This period uses publication dates.'],
        },
      });
    }),
  );
  const user = mount();
  await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
  await user.selectOptions(screen.getByLabelText('Eye time period'), '168');
  await user.type(screen.getByLabelText('Ask the Eye'), 'Summarise UK conflict reporting{Enter}');
  await screen.findByText('Two recent vessel observations are available.');
  expect(body?.time_range).toBeDefined();
  const since = Date.parse(String(body?.time_range?.since));
  const until = Date.parse(String(body?.time_range?.until));
  expect(until - since).toBe(168 * 3_600_000);
  expect(screen.getByText('Countries: GB')).toBeVisible();
  expect(screen.getByText('Topics: conflict')).toBeVisible();
  const href = screen.getByRole('link', { name: /Search deeper in Research/ }).getAttribute('href');
  const params = new URL(href ?? '', 'http://localhost').searchParams;
  expect(params.get('country')).toBe('GB');
  expect(params.get('since')).toBe('2026-09-11T00:00:00Z');
  expect(params.get('until')).toBe('2026-09-12T00:00:00Z');
  const subscriptionHref = screen
    .getByRole('link', { name: /Create subscription draft/ })
    .getAttribute('href');
  const subscription = new URL(subscriptionHref ?? '', 'http://localhost').searchParams;
  expect(subscription.get('country')).toBe('GB');
  expect(subscription.get('question')).toBe('Summarise UK conflict reporting');
});

it('narrows to selected source types while leaving automatic selection as the default', async () => {
  const bodies: AssistantRequest[] = [];
  server.use(
    http.post('/api/assistant/answer', async ({ request }) => {
      bodies.push((await request.json()) as AssistantRequest);
      return HttpResponse.json(eyeAnswer);
    }),
  );
  const user = mount();
  await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
  await user.click(screen.getByText('Source types'));
  await user.click(screen.getByRole('checkbox', { name: 'CCTV' }));
  await user.click(screen.getByRole('checkbox', { name: 'Cyber' }));
  await user.type(screen.getByLabelText('Ask the Eye'), 'Review these feeds{Enter}');
  await screen.findByText('Two recent vessel observations are available.');
  expect(bodies[0]?.source_categories).toEqual(['camera', 'cyber']);
  await user.click(screen.getByRole('button', { name: 'Use automatic selection' }));
  await user.type(screen.getByLabelText('Ask the Eye'), 'Review all relevant feeds{Enter}');
  await waitFor(() => expect(bodies).toHaveLength(2));
  expect(bodies[1]).not.toHaveProperty('source_categories');
  expect(bodies[1]).not.toHaveProperty('continuation_id');
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
  const selectSource = vi.fn(() => true);
  releaseMap = registerAssistantMapContext(
    () => ({ bounds: [-180, -90, 180, 90], selected: null }),
    focus,
    selectSource,
  );
  server.use(http.post('/api/assistant/answer', () => HttpResponse.json(eyeAnswer)));
  const user = mount();
  await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
  await user.type(screen.getByLabelText('Ask the Eye'), 'Locate a vessel.{Enter}');
  await screen.findByText('Two recent vessel observations are available.');
  await user.click(screen.getByText('Evidence and coverage'));
  await user.click(screen.getByRole('button', { name: 'Show on map' }));
  expect(focus).toHaveBeenCalledWith({ lon: 179.5, lat: 42 });
  expect(selectSource).toHaveBeenCalledWith({
    kind: 'event',
    id: 'vessel-1',
    point: { lon: 179.5, lat: 42 },
  });
});

it('copies a readable answer with citations and safe reference links', () => {
  const copied = answerWithReferences(eyeAnswer);
  expect(copied).toContain('Two recent vessel observations are available. [E1]');
  expect(copied).toContain('[E1] Example vessel position · aisstream · https://example.org/vessel');
  expect(copied).toContain('Coverage gap: AIS coverage is incomplete.');
  expect(copied).not.toContain('fixture-model');
  expect(
    answerWithReferences({
      ...eyeAnswer,
      sources: [{ ...eyeAnswer.sources[0]!, url: 'javascript:alert(1)' }],
    }),
  ).not.toContain('javascript:');
});
