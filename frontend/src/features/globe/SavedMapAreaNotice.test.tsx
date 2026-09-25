import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import { SavedMapAreaNotice } from './SavedMapAreaNotice';
import type { useSavedMapArea } from './useSavedMapArea';

type Area = ReturnType<typeof useSavedMapArea>;

function notice(overrides: Partial<Area>): Area {
  return {
    id: 'area-1',
    area: null,
    message: 'Showing the saved area.',
    close: vi.fn(),
    ...overrides,
  } as unknown as Area;
}

describe('SavedMapAreaNotice', () => {
  it('renders nothing without a saved area id', () => {
    const { container } = render(
      <MemoryRouter>
        <SavedMapAreaNotice area={notice({ id: null })} />
      </MemoryRouter>,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('names the area when known and closes on request', async () => {
    const user = userEvent.setup();
    const area = notice({ area: { name: 'Donbas watch' } as Area['area'] });
    render(
      <MemoryRouter>
        <SavedMapAreaNotice area={area} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Donbas watch')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Plans and areas' })).toHaveAttribute(
      'href',
      '/direction',
    );
    await user.click(screen.getByRole('button', { name: 'Close saved area' }));
    expect(area.close).toHaveBeenCalledTimes(1);
    render(
      <MemoryRouter>
        <SavedMapAreaNotice area={notice({})} />
      </MemoryRouter>,
    );
    expect(screen.getAllByText('Showing the saved area.')).toHaveLength(2);
  });
});
