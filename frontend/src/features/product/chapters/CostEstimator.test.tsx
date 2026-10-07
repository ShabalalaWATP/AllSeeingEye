import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { StoryMotionContext } from '../motion/useStoryMotion';
import { CostEstimator } from './CostEstimator';

function renderEstimator() {
  const user = userEvent.setup();
  render(
    <StoryMotionContext.Provider value={{ still: true, idle: true }}>
      <CostEstimator />
    </StoryMotionContext.Provider>,
  );
  return user;
}

function total(): string {
  return screen.getByText('Estimated monthly running cost').nextElementSibling?.textContent ?? '';
}

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
      'Server size',
    ]) {
      expect(screen.getByLabelText(label)).toBeInTheDocument();
    }
    expect(screen.getByRole('note')).toHaveTextContent(/Draft figures/);
    expect(screen.getByText('Quoted on enquiry')).toBeInTheDocument();
  });

  it('recalculates as the team grows and switches currency', async () => {
    const user = renderEstimator();
    const before = total();
    const analysts = screen.getByLabelText('Analysts');
    await user.clear(analysts);
    await user.type(analysts, '40');
    expect(total()).not.toBe(before);
    expect(total()).toMatch(/^£/);
    await user.click(screen.getByRole('radio', { name: 'USD' }));
    expect(total()).toMatch(/^US\$/);
  });

  it('fills the prices from the chosen price point', async () => {
    const user = renderEstimator();
    await user.selectOptions(screen.getByLabelText('Model price point'), 'frontier');
    expect(screen.getByLabelText('Input price, US$ per million tokens')).toHaveValue(15);
    expect(screen.getByLabelText('Output price, US$ per million tokens')).toHaveValue(75);
  });
});
