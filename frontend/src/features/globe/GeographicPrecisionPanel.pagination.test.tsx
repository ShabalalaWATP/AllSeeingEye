import { act, render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';

import { SETTLE_MS } from '@/lib/hooks/useSettledAnnouncement';
import { liveEvent } from '@/test/fixtures';
import { GeographicPrecisionPanel } from './GeographicPrecisionPanel';

it.each(['{Enter}', ' '])(
  'retains keyboard focus at both page boundaries when activated with %j',
  async (key) => {
    const records = Array.from({ length: 39 }, (_, index) =>
      liveEvent({ id: `record-${index}`, title: `Loaded record ${index}`, point: null }),
    );
    render(
      <GeographicPrecisionPanel
        events={records}
        hidden={[]}
        filter="all"
        onFilterChange={vi.fn()}
        onSelect={vi.fn()}
      />,
    );
    const user = userEvent.setup();
    const pages = screen.getByRole('navigation', { name: 'Location quality record pages' });
    const next = within(pages).getByRole('button', { name: 'Next' });
    const previous = within(pages).getByRole('button', { name: 'Previous' });
    const announced: string[] = [];
    const status = screen.getByRole('status');
    const observer = new MutationObserver(() => {
      if (status.textContent) announced.push(status.textContent);
    });
    observer.observe(status, { childList: true, subtree: true, characterData: true });
    const settle = () => act(() => new Promise((resolve) => setTimeout(resolve, SETTLE_MS + 1)));
    try {
      next.focus();
      await user.keyboard(key);
      expect(within(pages).getByText('2 / 2')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Loaded record 38/ })).toBeInTheDocument();
      expect(next).toHaveFocus();
      // A native disabled button loses focus in the browser even though jsdom retains it.
      expect(next).not.toBeDisabled();
      expect(next).toHaveAttribute('aria-disabled', 'true');
      await settle();
      expect(announced).toEqual(['39 matching loaded records, page 2 of 2.']);

      await user.keyboard('{Enter} ');
      await settle();
      expect(next).toHaveFocus();
      expect(within(pages).getByText('2 / 2')).toBeInTheDocument();
      expect(announced).toEqual(['39 matching loaded records, page 2 of 2.']);

      await user.tab({ shift: true });
      expect(previous).toHaveFocus();
      await user.keyboard(key);
      expect(within(pages).getByText('1 / 2')).toBeInTheDocument();
      expect(screen.getByText('Loaded record 0')).toBeInTheDocument();
      expect(previous).toHaveFocus();
      expect(previous).not.toBeDisabled();
      expect(previous).toHaveAttribute('aria-disabled', 'true');
      await settle();
      expect(announced).toEqual([
        '39 matching loaded records, page 2 of 2.',
        '39 matching loaded records, page 1 of 2.',
      ]);

      await user.keyboard('{Enter} ');
      await settle();
      expect(previous).toHaveFocus();
      expect(within(pages).getByText('1 / 2')).toBeInTheDocument();
      expect(announced).toHaveLength(2);
      await user.tab();
      expect(next).toHaveFocus();
    } finally {
      observer.disconnect();
    }
  },
);
