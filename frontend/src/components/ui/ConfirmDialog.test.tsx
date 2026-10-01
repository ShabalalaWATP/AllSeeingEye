import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { useRef, useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { installDialogStub } from '@/test/dialogStub';

import { ConfirmDialog } from './ConfirmDialog';

installDialogStub();

interface HarnessProps {
  busy?: boolean;
  error?: string | null;
  onConfirm?: () => void;
  removeTriggerOnConfirm?: boolean;
}

function Harness({ busy = false, error = null, onConfirm, removeTriggerOnConfirm }: HarnessProps) {
  const [open, setOpen] = useState(false);
  const [removed, setRemoved] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  return (
    <>
      <h2 ref={heading}>Saved things</h2>
      {removed ? null : (
        <button type="button" onClick={() => setOpen(true)}>
          Delete thing
        </button>
      )}
      <ConfirmDialog
        open={open}
        title="Delete “Thing”?"
        confirmLabel="Delete thing"
        busyLabel="Deleting thing…"
        busy={busy}
        error={error}
        returnFocus={heading}
        onCancel={() => setOpen(false)}
        onConfirm={() => {
          onConfirm?.();
          if (removeTriggerOnConfirm) {
            setRemoved(true);
            setOpen(false);
          }
        }}
      >
        <p>This permanently removes Thing. This cannot be undone.</p>
      </ConfirmDialog>
    </>
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ConfirmDialog', () => {
  it('renders nothing until it is opened', () => {
    render(<Harness />);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('names the decision, describes the consequence and focuses Cancel first', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole('button', { name: 'Delete thing' }));
    const dialog = await screen.findByRole('alertdialog', { name: 'Delete “Thing”?' });
    expect(dialog).toHaveAccessibleDescription(/permanently removes Thing/);
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toHaveFocus();
    expect(within(dialog).getByRole('button', { name: 'Delete thing' })).not.toHaveFocus();
  });

  it('cancels without confirming and returns focus to the trigger', async () => {
    const onConfirm = vi.fn();
    const user = userEvent.setup();
    render(<Harness onConfirm={onConfirm} />);
    const trigger = screen.getByRole('button', { name: 'Delete thing' });
    await user.click(trigger);
    await user.click(await screen.findByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(onConfirm).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(trigger).toHaveFocus();
    });
  });

  it('treats Escape as Cancel and keeps the key inside the dialog', async () => {
    const onConfirm = vi.fn();
    const pageKeys = vi.fn();
    document.addEventListener('keydown', pageKeys);
    const user = userEvent.setup();
    render(<Harness onConfirm={onConfirm} />);
    const trigger = screen.getByRole('button', { name: 'Delete thing' });
    await user.click(trigger);
    await screen.findByRole('alertdialog');
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(onConfirm).not.toHaveBeenCalled();
    expect(pageKeys).not.toHaveBeenCalled();
    document.removeEventListener('keydown', pageKeys);
    await waitFor(() => {
      expect(trigger).toHaveFocus();
    });
  });

  it('treats other close requests as Cancel, except while busy', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<Harness />);
    await user.click(screen.getByRole('button', { name: 'Delete thing' }));
    rerender(<Harness busy />);
    const busyRequest = new Event('cancel', { cancelable: true });
    fireEvent(await screen.findByRole('alertdialog'), busyRequest);
    expect(busyRequest.defaultPrevented).toBe(true);
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    rerender(<Harness />);
    fireEvent(screen.getByRole('alertdialog'), new Event('cancel', { cancelable: true }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('lets keyboard users reach and activate the confirming control', async () => {
    const onConfirm = vi.fn();
    const user = userEvent.setup();
    render(<Harness onConfirm={onConfirm} />);
    await user.click(screen.getByRole('button', { name: 'Delete thing' }));
    const dialog = await screen.findByRole('alertdialog');
    await user.tab();
    expect(within(dialog).getByRole('button', { name: 'Delete thing' })).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('shows progress, blocks repeats and cannot be dismissed while busy', async () => {
    const onConfirm = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(<Harness onConfirm={onConfirm} />);
    await user.click(screen.getByRole('button', { name: 'Delete thing' }));
    rerender(<Harness busy onConfirm={onConfirm} />);
    const dialog = await screen.findByRole('alertdialog');
    const confirm = within(dialog).getByRole('button', { name: 'Delete thing' });
    expect(confirm).toHaveAttribute('aria-busy', 'true');
    expect(confirm).toHaveTextContent('Deleting thing…');
    expect(within(dialog).getByRole('status')).toHaveTextContent('Deleting thing…');
    await user.click(confirm);
    await user.click(confirm);
    expect(onConfirm).not.toHaveBeenCalled();
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toBeDisabled();
    await user.keyboard('{Escape}');
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
  });

  it('keeps a failure visible inside the dialog and allows a retry', async () => {
    const onConfirm = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(<Harness onConfirm={onConfirm} />);
    await user.click(screen.getByRole('button', { name: 'Delete thing' }));
    rerender(<Harness error="You do not have permission." onConfirm={onConfirm} />);
    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).getByRole('alert')).toHaveTextContent('You do not have permission.');
    await user.click(within(dialog).getByRole('button', { name: 'Delete thing' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('falls back to the heading of the opener’s section when no target is given', async () => {
    function Sectioned() {
      const [state, setState] = useState<'idle' | 'open' | 'gone'>('idle');
      return (
        <section aria-label="Members">
          <h3>Team members</h3>
          {state === 'gone' ? null : (
            <button type="button" onClick={() => setState('open')}>
              Remove Uma
            </button>
          )}
          <ConfirmDialog
            open={state === 'open'}
            title="Remove Uma?"
            confirmLabel="Remove"
            busyLabel="Removing…"
            busy={false}
            error={null}
            onCancel={() => setState('idle')}
            onConfirm={() => setState('gone')}
          >
            <p>Uma loses access.</p>
          </ConfirmDialog>
        </section>
      );
    }
    const user = userEvent.setup();
    render(<Sectioned />);
    await user.click(screen.getByRole('button', { name: 'Remove Uma' }));
    await user.click(
      within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Remove' }),
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Team members' })).toHaveFocus();
    });
  });

  it('moves focus to the fallback heading when the trigger has gone', async () => {
    const user = userEvent.setup();
    render(<Harness removeTriggerOnConfirm />);
    await user.click(screen.getByRole('button', { name: 'Delete thing' }));
    await user.click(
      within(await screen.findByRole('alertdialog')).getByRole('button', {
        name: 'Delete thing',
      }),
    );
    const heading = screen.getByRole('heading', { name: 'Saved things' });
    await waitFor(() => {
      expect(heading).toHaveFocus();
    });
    expect(heading).toHaveAttribute('tabindex', '-1');
  });
});
