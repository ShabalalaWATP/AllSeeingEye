import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { expect, it, vi } from 'vitest';
import { publicFigure } from '@/test/fixtures.figures';
import { FigureInspector } from './FigureInspector';
import { FigureLocationPicker, figuresAtLocation } from './FigureLocationPicker';

const first = publicFigure({ id: 'first', name: 'First official', office: 'First office' });
const second = publicFigure({
  id: 'second',
  wikidata_id: 'Q123',
  name: 'Second official',
  office: 'Second office',
  portrait: null,
});
const nearby = publicFigure({
  id: 'nearby',
  name: 'Nearby official',
  placement: { ...first.placement, latitude: first.placement.latitude + 0.00001 },
});

it('offers only visible figures at identical coordinates, even when their placement basis differs', () => {
  const sharedSeat = {
    ...second,
    placement: { ...second.placement, basis: 'seat' as const },
  };
  expect(figuresAtLocation([first, nearby, sharedSeat], first)).toEqual([first, sharedSeat]);
  const onSelect = vi.fn();
  const { rerender } = render(
    <FigureLocationPicker
      figure={first}
      visibleFigures={[first, sharedSeat, nearby]}
      onSelect={onSelect}
    />,
  );
  expect(screen.getAllByRole('option')).toHaveLength(2);
  expect(screen.getByRole('option', { name: /Second official.*Seat of office/ })).toBeVisible();
  expect(screen.queryByRole('option', { name: /Nearby official/ })).not.toBeInTheDocument();
  expect(screen.getByRole('combobox')).toHaveAccessibleDescription(
    '2 visible figures share this map placement. This does not mean they are together.',
  );
  rerender(
    <FigureLocationPicker figure={first} visibleFigures={[first, nearby]} onSelect={onSelect} />,
  );
  expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  expect(onSelect).not.toHaveBeenCalled();
});

it('switches an overlapping selection without losing keyboard focus or changing coordinates', async () => {
  const user = userEvent.setup();
  const close = vi.fn();
  function Inspector() {
    const [selected, select] = useState(first);
    return (
      <FigureInspector
        figure={selected}
        visibleFigures={[first, second]}
        onSelectFigure={select}
        onClose={close}
      />
    );
  }
  render(<Inspector />);
  expect(screen.getByRole('button', { name: 'Close public figure details' })).toHaveFocus();
  await user.tab();
  const chooser = screen.getByRole('combobox', { name: 'Figure at this map location' });
  expect(chooser).toHaveFocus();
  await user.selectOptions(chooser, 'second');
  expect(screen.getByRole('heading', { name: 'Second official' })).toBeVisible();
  expect(chooser).toHaveValue('second');
  expect(chooser).toHaveFocus();
  expect(second.placement).toEqual(first.placement);
  expect(close).not.toHaveBeenCalled();
  await user.keyboard('{Escape}');
  expect(close).toHaveBeenCalledOnce();
});
