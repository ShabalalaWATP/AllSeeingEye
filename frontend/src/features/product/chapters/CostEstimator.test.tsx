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

  it('lets a field be cleared and retyped, settling out-of-range or blank input on blur', async () => {
    const user = renderEstimator();
    const analysts = screen.getByLabelText('Analysts');
    await user.clear(analysts);
    expect(analysts).toHaveValue(null);
    await user.type(analysts, '25');
    expect(analysts).toHaveValue(25);
    const at25 = total();
    await user.clear(analysts);
    await user.tab();
    expect(analysts).toHaveValue(25);
    expect(total()).toBe(at25);
    await user.clear(analysts);
    await user.type(analysts, '9000');
    await user.tab();
    expect(analysts).toHaveValue(500);

    const runs = screen.getByLabelText('Research runs per analyst per day');
    await user.clear(runs);
    await user.type(runs, '0.5');
    await user.tab();
    expect(runs).toHaveValue(0.5);

    const input = screen.getByLabelText('Input price, US$ per million tokens');
    await user.clear(input);
    await user.type(input, '12');
    await user.tab();
    expect(input).toHaveValue(12);
    const output = screen.getByLabelText('Output price, US$ per million tokens');
    await user.clear(output);
    await user.type(output, '2000');
    await user.tab();
    expect(output).toHaveValue(1000);
  });

  it('fills the prices from the chosen price point', async () => {
    const user = renderEstimator();
    await user.selectOptions(screen.getByLabelText('Model price point'), 'frontier');
    expect(screen.getByLabelText('Input price, US$ per million tokens')).toHaveValue(15);
    expect(screen.getByLabelText('Output price, US$ per million tokens')).toHaveValue(75);
  });
});
