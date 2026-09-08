import { act, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';

import { BritishGridPanel } from './BritishGridPanel';
import { CoordinateReadout } from './CoordinateReadout';
import type { CursorHandler } from './engine/MapEngine';
import type { GlobeEngineHandle } from './useGlobeEngine';

it('offers an explicit grid toggle, locate action and zoom guidance', async () => {
  const onToggle = vi.fn();
  const onLocate = vi.fn();
  render(<BritishGridPanel enabled onToggle={onToggle} onLocate={onLocate} zoom={2} />);
  expect(screen.getByRole('status')).toHaveTextContent('Zoom in');
  expect(screen.getByText(/No OSTN15/)).toBeVisible();
  await userEvent.click(screen.getByRole('checkbox', { name: 'Show British National Grid' }));
  await userEvent.click(screen.getByRole('button', { name: 'Locate Great Britain' }));
  expect(onToggle).toHaveBeenCalledOnce();
  expect(onLocate).toHaveBeenCalledOnce();
});

it('copies approximate BNG coordinates and clearly falls back outside its extent', async () => {
  let cursor: CursorHandler = () => undefined;
  const engine = {
    onCursor: (handler: CursorHandler) => {
      cursor = handler;
      return () => undefined;
    },
  } as GlobeEngineHandle;
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.assign(navigator, { clipboard: { writeText } });
  render(<CoordinateReadout engine={engine} bng />);
  act(() => cursor({ lon: -0.1278, lat: 51.5074 }));
  const button = screen.getByRole('button', { name: 'Copy coordinates' });
  expect(button).toHaveTextContent('BNG ≈ E');
  await userEvent.click(button);
  expect(writeText).toHaveBeenCalledWith(expect.stringMatching(/^BNG ≈ E/));
  act(() => cursor({ lon: 37.6, lat: 55.7 }));
  expect(button).toHaveTextContent('Outside BNG extent');
});
