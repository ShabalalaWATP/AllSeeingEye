import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SubscriptionCostNote } from './SubscriptionCostNote';
import { describeRelativeCost, relativeCost } from './subscriptionCost';

describe('subscription running cost', () => {
  it('treats a weekly Quick subscription as the baseline', () => {
    expect(relativeCost('weekly', 'quick', true)).toBe(1);
    expect(describeRelativeCost(1)).toBe('about the same as');
  });

  it('puts a daily Advanced subscription at roughly twenty times the baseline', () => {
    const multiple = relativeCost('daily', 'advanced', true);
    expect(multiple).toBeGreaterThan(19);
    expect(multiple).toBeLessThan(21);
    expect(describeRelativeCost(multiple)).toBe('about 20 times');
  });

  it('falls well below the baseline for occasional subscriptions', () => {
    expect(relativeCost('monthly', 'quick', true)).toBeLessThan(0.3);
    expect(relativeCost('weekly', 'advanced', false)).toBeLessThan(1);
  });

  it('states the daily Advanced consequence plainly at creation', () => {
    render(<SubscriptionCostNote cadence="weekly" depth="quick" researching />);
    const note = screen.getByRole('note');
    expect(note).toHaveTextContent('weekly Quick baseline');
    expect(note).toHaveTextContent('roughly twenty times a weekly Quick one');
  });

  it('names the multiple once a dearer shape is chosen', () => {
    render(<SubscriptionCostNote cadence="daily" depth="advanced" researching />);
    expect(screen.getByRole('note')).toHaveTextContent('about 20 times the model work');
  });
});
