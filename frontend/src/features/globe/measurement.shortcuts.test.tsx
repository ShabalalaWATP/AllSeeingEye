import { act, fireEvent, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { useMapMeasurement } from './useMapMeasurement';
const engine = { onClick: vi.fn(() => () => undefined) };
it('finishes and undoes with keys while preserving points after finishing', () => {
  const { result } = renderHook(() => useMapMeasurement(engine, true));
  act(() => {
    result.current.add(1, 2);
    result.current.setPicking(true);
  });
  fireEvent.keyDown(window, { key: 'Backspace' });
  expect(result.current.points).toHaveLength(0);
  act(() => result.current.add(3, 4));
  fireEvent.keyDown(window, { key: 'Enter' });
  expect(result.current.picking).toBe(false);
  fireEvent.keyDown(window, { key: 'Backspace' });
  expect(result.current.points).toHaveLength(1);
  act(() => result.current.setPicking(true));
  fireEvent.keyDown(window, { key: 'Escape' });
  expect(result.current.picking).toBe(false);
  expect(result.current.points).toHaveLength(1);
});
it('does not consume typing or shortcuts while input fields are edited or the tool is unavailable', () => {
  const { result, rerender } = renderHook(({ enabled }) => useMapMeasurement(engine, enabled), {
    initialProps: { enabled: true },
  });
  act(() => {
    result.current.add(1, 2);
    result.current.setPicking(true);
  });
  const field = document.createElement('input');
  document.body.append(field);
  for (const key of ['Enter', 'Escape', 'Backspace']) fireEvent.keyDown(field, { key });
  expect(result.current.picking).toBe(true);
  expect(result.current.points).toHaveLength(1);
  fireEvent.keyDown(window, { key: 'Backspace', ctrlKey: true });
  expect(result.current.points).toHaveLength(1);
  rerender({ enabled: false });
  fireEvent.keyDown(window, { key: 'Backspace' });
  expect(result.current.points).toHaveLength(1);
  field.remove();
});
