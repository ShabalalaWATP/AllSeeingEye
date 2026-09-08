import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { MapObjectDetails } from './MapObjectDetails';
it('moves focus to selected geometry details and restores the opener on Escape', () => {
  const opener = document.createElement('button');
  document.body.append(opener);
  opener.focus();
  const close = vi.fn();
  const { unmount } = render(
    <MapObjectDetails
      value={{
        title: 'Research area',
        notes: ['Operator-selected area'],
        feature: {
          type: 'Feature',
          id: 1,
          properties: { label: 'Area' },
          geometry: { type: 'Point', coordinates: [1, 2] },
        },
      }}
      onClose={close}
    />,
  );
  expect(screen.getByRole('button', { name: 'Close map object details' })).toHaveFocus();
  fireEvent.keyDown(window, { key: 'Escape' });
  expect(close).toHaveBeenCalledOnce();
  unmount();
  expect(opener).toHaveFocus();
  opener.remove();
});
