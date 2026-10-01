import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { installDialogStub } from '@/test/dialogStub';

import { ConfirmButton } from './ConfirmButton';

installDialogStub();

function Harness({ onConfirm }: { onConfirm: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  return (
    <>
      <ConfirmButton
        label="Archive"
        busy={busy}
        title="Archive “Morning brief”?"
        confirmLabel="Confirm archive"
        busyLabel="Archiving…"
        onConfirm={() => {
          setBusy(true);
          onConfirm()
            .then(() => setMessage('Archived.'))
            .catch(() => setMessage('Archive failed.'))
            .finally(() => setBusy(false));
        }}
      >
        <p>Future runs stop.</p>
      </ConfirmButton>
      {message === null ? null : <p role="status">{message}</p>}
    </>
  );
}

describe('ConfirmButton', () => {
  it('opens the confirmation and cancels without acting', async () => {
    const onConfirm = vi.fn(() => Promise.resolve());
    const user = userEvent.setup();
    render(<Harness onConfirm={onConfirm} />);
    const trigger = screen.getByRole('button', { name: 'Archive' });
    expect(trigger).toHaveAttribute('aria-haspopup', 'dialog');
    await user.click(trigger);
    const dialog = screen.getByRole('alertdialog', { name: 'Archive “Morning brief”?' });
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(onConfirm).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(trigger).toHaveFocus();
    });
  });

  it('stays open while the request runs, then closes once it settles', async () => {
    let finish: () => void = () => undefined;
    const onConfirm = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finish = resolve;
        }),
    );
    const user = userEvent.setup();
    render(<Harness onConfirm={onConfirm} />);
    await user.click(screen.getByRole('button', { name: 'Archive' }));
    const dialog = screen.getByRole('alertdialog');
    const confirm = within(dialog).getByRole('button', { name: 'Confirm archive' });
    await user.click(confirm);
    await user.click(confirm);
    expect(confirm).toHaveAttribute('aria-busy', 'true');
    expect(onConfirm).toHaveBeenCalledTimes(1);
    finish();
    await waitFor(() => {
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    });
    expect(screen.getByText('Archived.')).toBeInTheDocument();
  });

  it('closes after a failure so the caller’s error is visible beside the trigger', async () => {
    const onConfirm = vi.fn(() => Promise.reject(new Error('nope')));
    const user = userEvent.setup();
    render(<Harness onConfirm={onConfirm} />);
    await user.click(screen.getByRole('button', { name: 'Archive' }));
    await user.click(
      within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirm archive' }),
    );
    expect(await screen.findByText('Archive failed.')).toBeInTheDocument();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Archive' })).toBeEnabled();
  });
});
