import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { Ticker } from './Ticker';

it('keeps monthly baseline records out of the latest-events ticker', () => {
  const events = [
    liveEvent({
      id: 'old',
      title: 'July baseline',
      category: 'conflict',
      attributes: { dataset_status: 'provisional_monthly' },
    }),
    liveEvent({ id: 'now', title: 'Current report' }),
  ];
  render(
    <Ticker events={events} selectedId={null} now={Date.now()} onSelect={vi.fn()} limit={1} />,
  );
  expect(screen.getByRole('button', { name: /Current report/ })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /July baseline/ })).not.toBeInTheDocument();
});
