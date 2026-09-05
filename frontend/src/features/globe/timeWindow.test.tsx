import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { useState } from 'react';
import { expect, it } from 'vitest';

import { LayerPanel } from './LayerPanel';

function Controls() {
  const [hours, setHours] = useState<number | null>(null);
  return (
    <LayerPanel
      counts={{}}
      hidden={[]}
      stats={null}
      status="live"
      error={null}
      terminator
      lite={false}
      windowHours={hours}
      onWindow={setHours}
      onToggle={() => undefined}
      onToggleTerminator={() => undefined}
      onToggleLite={() => undefined}
      interference={false}
      onToggleInterference={() => undefined}
    />
  );
}

it('uses one tab stop and native arrow selection for the time window', async () => {
  const user = userEvent.setup();
  render(<Controls />);
  screen.getByRole('switch', { name: 'Economic 0' }).focus();
  await user.tab();
  expect(screen.getByRole('radio', { name: 'All' })).toHaveFocus();
  expect(screen.getByRole('radio', { name: 'All' })).toBeChecked();
  await user.keyboard('{ArrowRight}');
  expect(screen.getByRole('radio', { name: '1 h' })).toHaveFocus();
  expect(screen.getByRole('radio', { name: '1 h' })).toBeChecked();
  await user.keyboard('{ArrowLeft}');
  expect(screen.getByRole('radio', { name: 'All' })).toBeChecked();
  await user.keyboard('{ArrowUp}');
  expect(screen.getByRole('radio', { name: '7 d' })).toBeChecked();
  await user.tab();
  expect(screen.getByRole('switch', { name: 'Day and night on' })).toHaveFocus();
  await user.tab({ shift: true });
  expect(screen.getByRole('radio', { name: '7 d' })).toHaveFocus();
});
