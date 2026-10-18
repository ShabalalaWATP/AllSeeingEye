import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ALTERNATIVE, JUDGEMENTS, REPORT_HEADER, REPORT_NEXT } from '../content/research';
import { StoryMotionContext } from '../motion/useStoryMotion';
import { AssessChapter } from './AssessChapter';

function renderStill() {
  return render(
    <StoryMotionContext.Provider value={{ still: true, idle: true }}>
      <div className="product-story" data-motion="still">
        <AssessChapter />
      </div>
    </StoryMotionContext.Provider>,
  );
}

describe('Assess chapter when the story is still', () => {
  it('shows the finished report with its model details and judgements', () => {
    renderStill();
    const chapter = screen.getByRole('region', { name: 'Assess' });
    expect(chapter).toHaveAttribute('data-mode', 'still');
    expect(chapter.style.getPropertyValue('--progress')).toBe('1.0000');
    const report = screen.getByRole('article', { name: 'Example assessment' });
    expect(within(report).getByText(REPORT_HEADER.model)).toBeInTheDocument();
    expect(REPORT_HEADER.model).toContain('Model: your configured provider');
    // No model is bundled, so the page never names one as if it were.
    expect(report.textContent).not.toMatch(/\b(gpt|claude|llama|gemini|mistral|titan)\b/i);
    for (const judgement of JUDGEMENTS)
      expect(within(report).getByText(judgement.text, { exact: false })).toBeInTheDocument();
  });

  it('shows the challenge, the alternative explanation and the closing beat', () => {
    renderStill();
    expect(screen.getByText(/Challenged: confidence held at moderate/)).toBeInTheDocument();
    expect(screen.getByText(ALTERNATIVE)).toBeInTheDocument();
    const next = screen.getByRole('list', { name: 'What happens next' });
    const steps = within(next)
      .getAllByRole('listitem')
      .map((item) => item.textContent);
    expect(steps).toEqual([...REPORT_NEXT]);
  });

  it('hides the decorative citation threads from screen readers', () => {
    const { container } = renderStill();
    const threads = container.querySelector('.assess-threads');
    expect(threads).toHaveAttribute('aria-hidden', 'true');
    const cited = JUDGEMENTS.reduce((sum, judgement) => sum + judgement.cites.length, 0);
    expect(threads?.querySelectorAll('path.draw-path')).toHaveLength(cited);
  });
});
