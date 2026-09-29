import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Timeline } from './TrackerParts';

const buckets = [
  { day: '2026-09-01', count: 12, max_severity: 0.9 },
  { day: '2026-09-02', count: 3, max_severity: 0.5 },
  { day: '2026-09-03', count: 1, max_severity: 0.85 },
  { day: '2026-09-04', count: 0, max_severity: null },
];

describe('Timeline severity', () => {
  it('names high-severity days in the text alternative, not only by colour', () => {
    render(<Timeline buckets={buckets} label="Events by day" />);
    expect(
      screen.getByRole('img', {
        name:
          'Events by day: 2026-09-01: 12 events, high severity; 2026-09-02: 3 events; ' +
          '2026-09-03: 1 event, high severity; 2026-09-04: 0 events',
      }),
    ).toBeInTheDocument();
    expect(screen.getByTitle('2026-09-01: 12 events, high severity')).toBeInTheDocument();
    expect(screen.getByTitle('2026-09-02: 3 events')).toBeInTheDocument();
  });

  it('marks high-severity bars with a shape as well as a colour', () => {
    render(<Timeline buckets={buckets} label="Events by day" />);
    const high = screen.getByTitle('2026-09-01: 12 events, high severity');
    const threshold = screen.getByTitle('2026-09-03: 1 event, high severity');
    const ordinary = screen.getByTitle('2026-09-02: 3 events');
    expect(high).toHaveAttribute('data-severity', 'high');
    expect(threshold).toHaveAttribute('data-severity', 'high');
    expect(ordinary).not.toHaveAttribute('data-severity');
    expect(high.querySelector('[data-severity-marker]')).not.toBeNull();
    expect(ordinary.querySelector('[data-severity-marker]')).toBeNull();
  });

  it('explains both bar styles in a legend', () => {
    render(<Timeline buckets={buckets} label="Conflict events by day" />);
    const legend = screen.getByRole('list', { name: 'Conflict events by day legend' });
    const items = within(legend).getAllByRole('listitem');
    expect(items.map((item) => item.textContent)).toEqual([
      'Events per day',
      'High severity (0.85 / 1 or above)',
    ]);
    expect(items[1]!.querySelector('[data-severity-marker]')).not.toBeNull();
  });
});
