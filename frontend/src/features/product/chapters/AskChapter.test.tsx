import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ASK_FEATURES, EXAMPLE_QUESTION } from '../content/research';
import { StoryMotionContext } from '../motion/useStoryMotion';
import { AskChapter } from './AskChapter';

function renderStill() {
  return render(
    <StoryMotionContext.Provider value={{ still: true, idle: true }}>
      <div className="product-story" data-motion="still">
        <AskChapter />
      </div>
    </StoryMotionContext.Provider>,
  );
}

describe('Ask chapter when the story is still', () => {
  it('shows the final scene: full question, every scope chip and the deepest depth', () => {
    renderStill();
    const chapter = screen.getByRole('region', { name: 'Ask' });
    expect(chapter).toHaveAttribute('data-mode', 'still');
    expect(chapter.style.getPropertyValue('--progress')).toBe('1.0000');
    const typed = within(chapter).getAllByText(EXAMPLE_QUESTION);
    expect(typed.some((node) => node.classList.contains('sr-only'))).toBe(true);
    expect(typed.some((node) => node.closest('[aria-hidden="true"]') !== null)).toBe(true);
    const area = within(chapter).getByText('Drawn on the map').closest('li');
    expect(area).toHaveAttribute('data-from-map', 'true');
    expect(area).toHaveTextContent('Area');
    expect(within(chapter).getByText('Advanced').closest('li')).toHaveAttribute(
      'data-selected',
      'true',
    );
  });

  it('explains scope, Research Briefs and private inputs in plain text', () => {
    renderStill();
    for (const feature of ASK_FEATURES) expect(screen.getByText(feature)).toBeInTheDocument();
    expect(screen.getByText(/Private documents and media as inputs/)).toBeInTheDocument();
    expect(screen.getByText(/Research Briefs keep explicit requirements/)).toBeInTheDocument();
    expect(screen.getByText(/Illustrative request/)).toBeInTheDocument();
  });

  it('hides the decorative window chrome and caret from screen readers', () => {
    const { container } = renderStill();
    expect(container.querySelector('.console-bar')).toHaveAttribute('aria-hidden', 'true');
    const caret = container.querySelector('.console-caret');
    expect(caret?.closest('[aria-hidden="true"]')).not.toBeNull();
  });
});
