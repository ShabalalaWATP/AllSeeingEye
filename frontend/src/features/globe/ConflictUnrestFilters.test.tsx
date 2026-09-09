import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { ConflictFilterPanel } from './ConflictFilterPanel';
import { useConflictFilters } from './useConflictFilters';

it('offers separate labelled unrest filters with matching visual legends', () => {
  const events = [
    liveEvent({ id: 'peaceful', category: 'conflict', subtype: 'protest' }),
    liveEvent({ id: 'violent', category: 'conflict', subtype: 'riot' }),
  ];
  function Harness() {
    const filters = useConflictFilters(events);
    return (
      <>
        <ConflictFilterPanel {...filters} />
        <output aria-label="Shown reports">
          {filters.filtered.map((event) => event.id).join(',')}
        </output>
      </>
    );
  }
  render(<Harness />);
  const protest = screen.getByRole('radio', { name: 'Protests / demonstrations 1 loaded reports' });
  const riot = screen.getByRole('radio', {
    name: 'Riots / violent demonstrations 1 loaded reports',
  });
  const protestPath = protest.closest('label')?.querySelector('svg path')?.getAttribute('d');
  const riotPath = riot.closest('label')?.querySelector('svg path')?.getAttribute('d');
  expect(protestPath).toBeTruthy();
  expect(riotPath).not.toBe(protestPath);
  fireEvent.click(protest);
  expect(screen.getByLabelText('Shown reports')).toHaveTextContent(/^peaceful$/);
  fireEvent.click(riot);
  expect(screen.getByLabelText('Shown reports')).toHaveTextContent(/^violent$/);
  expect(screen.getByText(/Does not assume protester violence/)).toBeVisible();
  expect(screen.getByText(/do not establish armed conflict/)).toBeVisible();
});
