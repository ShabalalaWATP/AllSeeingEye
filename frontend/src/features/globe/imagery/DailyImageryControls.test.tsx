import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';

import { DailyImageryAttribution } from './DailyImageryAttribution';
import { DailyImageryControls } from './DailyImageryControls';
import { selectDailyImagery, useDailyImageryStore } from './dailyImageryStore';

const today = new Date().toISOString().slice(0, 10);
const yesterday = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);

describe('daily imagery controls', () => {
  beforeEach(() => {
    useDailyImageryStore.getState().reset();
  });

  it('is off by default and explains its resolution and source when switched on', async () => {
    const user = userEvent.setup();
    render(
      <>
        <DailyImageryControls />
        <DailyImageryAttribution />
      </>,
    );
    const toggle = screen.getByRole('switch', { name: 'Daily satellite imagery' });
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    expect(selectDailyImagery(useDailyImageryStore.getState())).toBeNull();
    expect(screen.queryByRole('link', { name: /NASA GIBS/ })).not.toBeInTheDocument();

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    const date = screen.getByLabelText('Imagery date (UTC)');
    expect(date).toHaveValue(yesterday);
    expect(date).toHaveAttribute('min', '2000-02-24');
    expect(date).toHaveAttribute('max', today);
    expect(screen.getByText(/roughly 250 m to 1 km/)).toBeVisible();
    expect(screen.getByText(/globe and the flat map/)).toBeVisible();
    expect(screen.getAllByRole('link', { name: /NASA GIBS/ }).length).toBeGreaterThan(0);
    expect(screen.getByText(/MODIS Terra true colour.*for/)).toBeVisible();
    expect(selectDailyImagery(useDailyImageryStore.getState())).toEqual({
      product: 'modis_terra',
      date: yesterday,
    });

    await user.selectOptions(screen.getByLabelText('Imagery product'), 'viirs_snpp');
    expect(date).toHaveAttribute('min', '2015-11-24');
  });

  it('refuses an out-of-range date instead of requesting tiles for it', async () => {
    const user = userEvent.setup();
    render(<DailyImageryControls />);
    await user.click(screen.getByRole('switch', { name: 'Daily satellite imagery' }));
    await user.selectOptions(screen.getByLabelText('Imagery product'), 'viirs_snpp');
    fireEvent.change(screen.getByLabelText('Imagery date (UTC)'), {
      target: { value: '2014-06-01' },
    });
    expect(screen.getByText(/Choose a date from 24 Nov\w* 2015/)).toBeVisible();
    expect(selectDailyImagery(useDailyImageryStore.getState())).toBeNull();
  });

  it('reports failed tiles without hiding the base map, and clears on a new date', async () => {
    const user = userEvent.setup();
    render(<DailyImageryControls />);
    await user.click(screen.getByRole('switch', { name: 'Daily satellite imagery' }));
    useDailyImageryStore.getState().markFailed();
    expect(await screen.findByText(/Some imagery tiles did not load/)).toBeVisible();
    fireEvent.change(screen.getByLabelText('Imagery date (UTC)'), {
      target: { value: '2026-01-15' },
    });
    expect(screen.queryByText(/Some imagery tiles did not load/)).not.toBeInTheDocument();
  });
});
