import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';
import { applySession } from '@/test/render';
import { server } from '@/test/server';
import { EyeAssistant } from './EyeAssistant';
import { eyeAnswer } from './assistantFixture';

afterEach(() => vi.unstubAllGlobals());

async function mount() {
  applySession('user');
  render(
    <MemoryRouter>
      <EyeAssistant />
    </MemoryRouter>,
  );
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
  return user;
}

it('expands near full screen and restores without losing the draft or reopening the dialog', async () => {
  const user = await mount();
  const panel = screen.getByRole('dialog');
  const compactWidth = panel.style.width;
  const compactHeight = panel.style.height;
  await user.type(screen.getByLabelText('Ask the Eye'), 'My unfinished question');
  await user.click(screen.getByRole('button', { name: 'Expand chat' }));
  expect(screen.getByRole('dialog')).toBe(panel);
  expect(parseFloat(panel.style.width)).toBeGreaterThan(window.innerWidth * 0.9);
  expect(parseFloat(panel.style.width)).toBeLessThan(window.innerWidth);
  expect(parseFloat(panel.style.height)).toBeGreaterThan(window.innerHeight * 0.9);
  expect(parseFloat(panel.style.height)).toBeLessThan(window.innerHeight);
  expect(screen.getByRole('button', { name: 'Restore compact chat' })).toHaveFocus();
  await user.click(screen.getByRole('button', { name: 'Restore compact chat' }));
  expect(panel.style.width).toBe(compactWidth);
  expect(panel.style.height).toBe(compactHeight);
  expect(screen.getByLabelText('Ask the Eye')).toHaveValue('My unfinished question');
});

it('keeps the expanded panel and wider launcher inside the viewport after resizing', async () => {
  const user = await mount();
  await user.click(screen.getByRole('button', { name: 'Expand chat' }));
  vi.stubGlobal('innerWidth', 320);
  vi.stubGlobal('innerHeight', 568);
  await act(() => fireEvent(window, new Event('resize')));
  const panel = screen.getByRole('dialog');
  expect(parseFloat(panel.style.left)).toBeGreaterThanOrEqual(12);
  expect(parseFloat(panel.style.top)).toBeGreaterThanOrEqual(16);
  expect(parseFloat(panel.style.left) + parseFloat(panel.style.width)).toBeLessThanOrEqual(308);
  expect(parseFloat(panel.style.top) + parseFloat(panel.style.height)).toBeLessThanOrEqual(552);
  const launcher = screen.getByRole('button', { name: 'Minimise Eye assistant' });
  expect(parseFloat(launcher.style.left) + parseFloat(launcher.style.width)).toBeLessThanOrEqual(
    308,
  );
  await user.click(screen.getByRole('button', { name: 'Restore compact chat' }));
  expect(parseFloat(panel.style.width)).toBeLessThanOrEqual(296);
});

it('expanding and restoring preserves an in-flight answer without duplicate requests', async () => {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let calls = 0;
  server.use(
    http.post('/api/assistant/answer', async () => {
      calls++;
      await gate;
      return HttpResponse.json(eyeAnswer);
    }),
  );
  const user = await mount();
  await user.type(screen.getByLabelText('Ask the Eye'), 'Where are the ships?{Enter}');
  await waitFor(() => expect(calls).toBe(1));
  await user.click(screen.getByRole('button', { name: 'Expand chat' }));
  await user.click(screen.getByRole('button', { name: 'Restore compact chat' }));
  expect(screen.getByRole('button', { name: 'Stop' })).toBeEnabled();
  await act(async () => {
    release();
    await gate;
  });
  expect(await screen.findByText('Two recent vessel observations are available.')).toBeVisible();
  expect(calls).toBe(1);
});
