import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { HistoricalBaselineNote } from './HistoricalBaselineNote';

it('labels historical releases and occurrence dates separately from live observations', () => {
  render(
    <HistoricalBaselineNote
      event={liveEvent({
        category: 'conflict',
        attributes: {
          dataset_status: 'provisional_monthly',
          dataset_version: '26.0.7',
          coverage_start: '2026-07-01',
          coverage_end: '2026-07-31',
          occurrence_start: '2026-07-14T00:00:00Z',
        },
      })}
    />,
  );
  expect(screen.getByText(/Historical baseline, not a live incident/)).toHaveTextContent('26.0.7');
  expect(screen.getByText(/coverage 2026-07-01 to 2026-07-31/)).toHaveTextContent(
    'Occurred: 2026-07-14',
  );
});

it('does not label current reports as historical and does not invent missing metadata', () => {
  const { container, rerender } = render(<HistoricalBaselineNote event={liveEvent()} />);
  expect(container).toBeEmptyDOMElement();
  rerender(
    <HistoricalBaselineNote
      event={liveEvent({ category: 'conflict', tags: ['provisional_monthly'] })}
    />,
  );
  expect(screen.getByText(/dataset Unknown/)).toHaveTextContent('coverage Unknown to Unknown');
});
