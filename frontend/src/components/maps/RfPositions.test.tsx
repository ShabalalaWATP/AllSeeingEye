import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { RfPositions } from './RfPositions';
it('offers precise entry for both named sites and allows swapping only complete links', () => {
  const swap = vi.fn(),
    setSite = vi.fn();
  const { rerender } = render(
    <RfPositions onSetSite={setSite} onSwapSites={swap} onPick={vi.fn()} />,
  );
  expect(screen.getByRole('button', { name: 'Swap transmitter and receiver' })).toBeDisabled();
  fireEvent.click(screen.getByText('Enter precise sites'));
  expect(screen.getByLabelText('Receiver latitude')).toHaveValue('');
  rerender(
    <RfPositions
      origin={[0, 51]}
      receiver={[1, 52]}
      siteNames={{ origin: 'Hill', receiver: 'Valley' }}
      onSetSite={setSite}
      onSwapSites={swap}
      onPick={vi.fn()}
    />,
  );
  expect(screen.getByText('Hill')).toBeVisible();
  expect(screen.getByText('Valley')).toBeVisible();
  expect(screen.getByLabelText('Transmitter latitude')).toHaveValue('51');
  fireEvent.click(screen.getByRole('button', { name: 'Swap transmitter and receiver' }));
  expect(swap).toHaveBeenCalledOnce();
});
it('arms and cancels explicit drag placement separately from click placement', () => {
  const drag = vi.fn(),
    pick = vi.fn();
  const { rerender } = render(<RfPositions origin={[0, 51]} onDragSite={drag} onPick={pick} />);
  expect(screen.getByRole('button', { name: 'Drag receiver' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Drag transmitter' }));
  expect(drag).toHaveBeenCalledWith('origin');
  rerender(
    <RfPositions
      origin={[0, 51]}
      receiver={[1, 51]}
      onDragSite={drag}
      onPick={pick}
      interaction="drag"
      picking="origin"
    />,
  );
  expect(screen.getByRole('status')).toHaveTextContent('Drag the existing site marker');
  fireEvent.click(screen.getByRole('button', { name: 'Drag transmitter' }));
  expect(pick).toHaveBeenCalledWith(null);
  fireEvent.click(screen.getByRole('button', { name: 'Drag receiver' }));
  expect(drag).toHaveBeenLastCalledWith('receiver');
  rerender(
    <RfPositions
      origin={[0, 51]}
      receiver={[1, 51]}
      onDragSite={drag}
      interaction="drag"
      picking="receiver"
    />,
  );
  fireEvent.click(screen.getByRole('button', { name: 'Drag receiver' }));
  expect(drag).toHaveBeenCalledTimes(2);
});
it('shows receiver placement guidance, cancels an armed click, and removes the receiver', () => {
  const pick = vi.fn(),
    clear = vi.fn();
  const { rerender } = render(
    <RfPositions
      origin={[0, 51]}
      receiver={[1, 51]}
      picking="receiver"
      onPick={pick}
      onClearReceiver={clear}
      pathActive={false}
    />,
  );
  expect(screen.getByRole('status')).toHaveTextContent('place the receiver');
  expect(screen.queryByText(/Path length follows/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Move receiver' }));
  expect(pick).toHaveBeenCalledWith(null);
  fireEvent.click(screen.getByRole('button', { name: 'Remove receiver, keep transmitter' }));
  expect(clear).toHaveBeenCalledOnce();
  rerender(<RfPositions origin={[0, 51]} onPick={pick} />);
  fireEvent.click(screen.getByRole('button', { name: 'Add receiver' }));
  expect(pick).toHaveBeenLastCalledWith('receiver');
});
