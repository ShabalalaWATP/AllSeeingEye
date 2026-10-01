import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { Button } from './Button';

function PendingForm({ onSubmit }: { onSubmit: () => void }) {
  const [busy, setBusy] = useState(false);
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
        setBusy(true);
      }}
    >
      <Button type="submit" busy={busy}>
        Save
      </Button>
    </form>
  );
}

describe('Button', () => {
  it('stays focusable while busy and marks itself unavailable', () => {
    render(<Button busy>Save</Button>);
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toBeEnabled();
    expect(button).toHaveAttribute('aria-disabled', 'true');
    expect(button).toHaveAttribute('aria-busy', 'true');
    button.focus();
    expect(button).toHaveFocus();
  });

  it('ignores activation while busy', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(
      <Button busy onClick={onClick}>
        Save
      </Button>,
    );
    await user.click(screen.getByRole('button', { name: 'Save' }));
    await user.keyboard('{Enter} ');
    expect(onClick).not.toHaveBeenCalled();
  });

  it('keeps focus on a submit button and blocks resubmission while busy', async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<PendingForm onSubmit={onSubmit} />);
    const button = screen.getByRole('button', { name: 'Save' });
    await user.click(button);
    expect(button).toHaveAttribute('aria-disabled', 'true');
    expect(button).toHaveFocus();
    await user.click(button);
    await user.keyboard('{Enter}');
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(button).toHaveFocus();
  });

  it('keeps the native disabled state for an explicitly disabled button', () => {
    render(
      <Button disabled busy>
        Save
      </Button>,
    );
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
  });

  it('is fully available when idle', () => {
    render(<Button>Save</Button>);
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toBeEnabled();
    expect(button).not.toHaveAttribute('aria-disabled');
    expect(button).toHaveAttribute('aria-busy', 'false');
    expect(button.querySelector('[data-busy-indicator]')).toBeNull();
  });

  it('shows a visible progress indicator whenever it is busy', () => {
    render(<Button busy>Save</Button>);
    const indicator = screen
      .getByRole('button', { name: 'Save' })
      .querySelector('[data-busy-indicator]');
    expect(indicator).not.toBeNull();
    expect(indicator).toHaveAttribute('aria-hidden', 'true');
  });

  it('shows a busy label and announces it while keeping its accessible name', () => {
    const { rerender } = render(<Button busyLabel="Saving…">Save</Button>);
    const status = screen.getByRole('status');
    expect(status).toBeEmptyDOMElement();
    rerender(
      <Button busy busyLabel="Saving…">
        Save
      </Button>,
    );
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toHaveTextContent('Saving…');
    expect(status).toHaveTextContent('Saving…');
    rerender(<Button busyLabel="Saving…">Save</Button>);
    expect(button).toHaveTextContent(/^Save$/);
    expect(status).toBeEmptyDOMElement();
  });

  it('forwards a ref to the native button', () => {
    let node: HTMLButtonElement | null = null;
    render(
      <Button
        ref={(element) => {
          node = element;
        }}
      >
        Save
      </Button>,
    );
    expect(node).toBe(screen.getByRole('button', { name: 'Save' }));
  });
});
