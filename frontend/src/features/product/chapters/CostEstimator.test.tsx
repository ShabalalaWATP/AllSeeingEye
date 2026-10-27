import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { listAssumptions } from '../content/costing';
import { EnquiryPrefillContext, type EnquiryPrefill } from '../enquiry/enquiryPrefill';
import { StoryMotionContext } from '../motion/useStoryMotion';
import { CostEstimator } from './CostEstimator';

function renderEstimator(prefill?: EnquiryPrefill) {
  const user = userEvent.setup();
  const estimator = (
    <StoryMotionContext.Provider value={{ still: true, idle: true }}>
      <CostEstimator />
    </StoryMotionContext.Provider>
  );
  render(
    prefill === undefined ? (
      estimator
    ) : (
      <EnquiryPrefillContext.Provider value={prefill}>{estimator}</EnquiryPrefillContext.Provider>
    ),
  );
  return user;
}

function total(): string {
  return screen.getByTestId('estimate-total').querySelector(':scope > .sr-only')?.textContent ?? '';
}

afterEach(() => {
  vi.useRealTimers();
});

describe('cost estimator', () => {
  it('labels every input and says the figures are a draft', () => {
    renderEstimator();
    for (const label of [
      'Analysts',
      'Research runs per analyst per day',
      'Typical depth',
      'Model price point',
      'Input price, US$ per million tokens',
      'Output price, US$ per million tokens',
      'Extra for the assistant, briefings and subscriptions, percent (optional)',
      'Server size',
    ]) {
      expect(screen.getByLabelText(label)).toBeInTheDocument();
    }
    expect(screen.getByRole('note')).toHaveTextContent(/Draft figures/);
    expect(screen.getByText('Quoted on enquiry')).toBeInTheDocument();
    // A still story shows the settled figures straight away.
    expect(total()).toMatch(/^£[\d,]+ to £[\d,]+$/);
    expect(screen.getByTestId('estimate-total')).toHaveTextContent(total());
  });

  it('recalculates as the team grows and switches between all three currencies', async () => {
    const user = renderEstimator();
    const before = total();
    const analysts = screen.getByLabelText('Analysts');
    await user.clear(analysts);
    await user.type(analysts, '40');
    expect(total()).not.toBe(before);
    expect(total()).toMatch(/^£/);
    await user.click(screen.getByRole('radio', { name: 'USD' }));
    expect(total()).toMatch(/^US\$/);
    await user.click(screen.getByRole('radio', { name: 'EUR' }));
    expect(total()).toMatch(/^€/);
  });

  it('reports blank and out-of-range figures instead of clamping them silently', async () => {
    const user = renderEstimator();
    const analysts = screen.getByLabelText('Analysts');
    await user.clear(analysts);
    await user.type(analysts, '25');
    const at25 = total();
    expect(analysts).not.toHaveAttribute('aria-invalid');

    await user.clear(analysts);
    await user.tab();
    expect(analysts).toHaveValue(null);
    expect(analysts).toHaveAttribute('aria-invalid', 'true');
    expect(analysts).toHaveAccessibleDescription(
      'Analysts is required: enter a whole number from 1 to 500.',
    );
    // The estimate keeps the last valid figure while the field is wrong.
    expect(total()).toBe(at25);

    await user.type(analysts, '9000');
    expect(analysts).toHaveValue(9000);
    const error = screen.getByText('Analysts must be a whole number from 1 to 500.');
    expect(error).toHaveAttribute('aria-live', 'polite');
    // Typing went through 90, the last figure in range, which the estimate still uses.
    const at90 = total();
    await user.type(analysts, '0');
    expect(total()).toBe(at90);

    await user.clear(analysts);
    await user.type(analysts, '500');
    expect(analysts).not.toHaveAttribute('aria-invalid');
    expect(screen.queryByText(/Analysts must be/)).toBeNull();

    const output = screen.getByLabelText('Output price, US$ per million tokens');
    await user.clear(output);
    await user.type(output, '2000');
    expect(output).toHaveAccessibleDescription('Output price must be a number from 0 to 1,000.');

    const runs = screen.getByLabelText('Research runs per analyst per day');
    await user.clear(runs);
    await user.type(runs, '0.5');
    expect(runs).not.toHaveAttribute('aria-invalid');
  });

  it('treats the uplift as optional but bounded', async () => {
    const user = renderEstimator();
    const uplift = screen.getByLabelText(/Extra for the assistant/);
    expect(uplift).toHaveValue(25);
    expect(uplift).toHaveAccessibleDescription('Leave blank for the default of 25 percent.');
    const before = total();
    await user.clear(uplift);
    expect(uplift).not.toHaveAttribute('aria-invalid');
    expect(total()).toBe(before);
    await user.type(uplift, '0');
    expect(total()).not.toBe(before);
    await user.clear(uplift);
    await user.type(uplift, '250');
    expect(uplift).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('The extra percentage must be a number from 0 to 200.')).toBeVisible();
  });

  it('fills the prices from the chosen price point', async () => {
    const user = renderEstimator();
    await user.selectOptions(screen.getByLabelText('Model price point'), 'frontier');
    expect(screen.getByLabelText('Input price, US$ per million tokens')).toHaveValue(15);
    expect(screen.getByLabelText('Output price, US$ per million tokens')).toHaveValue(75);
  });

  it('discloses every figure with its source and checked date', async () => {
    const user = renderEstimator();
    const disclosure = screen.getByText('Assumptions, sources and checked dates');
    await user.click(disclosure);
    const items = within(disclosure.closest('details')!).getAllByRole('listitem');
    expect(items).toHaveLength(listAssumptions().length);
    expect(items[0]).toHaveTextContent(/Small server.*Source: Draft indicative range/);
    expect(items[0]).toHaveTextContent('Checked 7 October 2026.');
    expect(
      items.filter((item) => item.textContent.includes('Source: Draft placeholder')),
    ).toHaveLength(4);
  });

  it('says the figures are under review once any is older than 90 days', () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2027, 0, 6, 12));
    renderEstimator();
    expect(screen.getByText(/^Figures under review:/)).toHaveTextContent(
      'Figures under review: 12 of the figures behind this estimate were last checked more than 90 days ago.',
    );
  });

  it('shows no review note while every figure is recent', () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 9, 18, 12));
    renderEstimator();
    expect(screen.queryByText(/Figures under review/)).toBeNull();
  });

  it('offers the estimate to the enquiry form only when one is on the page', async () => {
    const offer = vi.fn();
    const user = renderEstimator({ available: true, offer, receive: () => () => undefined });
    await user.selectOptions(screen.getByLabelText('Model price point'), 'economy');
    await user.click(screen.getByRole('button', { name: 'Send this estimate with an enquiry' }));
    expect(offer).toHaveBeenCalledTimes(1);
    const text = String(offer.mock.calls[0]?.[0]);
    expect(text).toContain('This is an estimate, not a quote.');
    expect(text).toContain('Model prices: Economy model');
    expect(text).toContain(`Total: ${total()}`);

    await user.clear(screen.getByLabelText('Input price, US$ per million tokens'));
    await user.type(screen.getByLabelText('Input price, US$ per million tokens'), '1');
    await user.click(screen.getByRole('button', { name: 'Send this estimate with an enquiry' }));
    expect(String(offer.mock.calls[1]?.[0])).toContain('Model prices: Custom prices');

    await user.clear(screen.getByLabelText('Analysts'));
    const send = screen.getByRole('button', { name: 'Send this estimate with an enquiry' });
    expect(send).toBeDisabled();
    expect(send).toHaveAccessibleDescription('Correct the marked figures to send this estimate.');
  });

  it('hides the hand-off when this installation takes no enquiries', () => {
    renderEstimator();
    expect(screen.queryByRole('button', { name: /Send this estimate/ })).toBeNull();
  });
});
