import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { EVIDENCE, SHARED_ORIGIN } from '../content/research';
import { fanPath } from '../motion/useFanPaths';
import { StoryMotionContext } from '../motion/useStoryMotion';
import { CollectChapter } from './CollectChapter';

function renderStill() {
  return render(
    <StoryMotionContext.Provider value={{ still: true, idle: true }}>
      <div className="product-story" data-motion="still">
        <CollectChapter />
      </div>
    </StoryMotionContext.Provider>,
  );
}

describe('Collect chapter when the story is still', () => {
  it('shows every evidence card with its grade, time and receipt', () => {
    renderStill();
    const chapter = screen.getByRole('region', { name: 'Collect' });
    expect(chapter).toHaveAttribute('data-mode', 'still');
    expect(chapter.style.getPropertyValue('--progress')).toBe('1.0000');
    const list = screen.getByRole('list', { name: 'Example evidence collected for the question' });
    const cards = within(list).getAllByRole('listitem');
    expect(cards).toHaveLength(EVIDENCE.length);
    EVIDENCE.forEach((card, index) => {
      expect(cards[index]).toHaveTextContent(card.title);
      expect(cards[index]).toHaveTextContent(`Receipt ${card.receipt}`);
    });
  });

  it('keeps the collection gap visibly empty and explains shared origins', () => {
    renderStill();
    const gap = screen.getByText('No independent satellite confirmation found').closest('li');
    expect(gap).toHaveAttribute('data-gap', 'true');
    expect(gap).toHaveTextContent('Gap recorded');
    expect(within(gap as HTMLElement).getByLabelText('Collection gap')).toBeInTheDocument();
    expect(screen.getByText(SHARED_ORIGIN)).toBeInTheDocument();
    expect(screen.getByText(/Illustrative evidence/)).toBeInTheDocument();
  });

  it('draws one decorative arc per card from the scope, hidden from screen readers', () => {
    const { container } = renderStill();
    const arcs = container.querySelector('.collect-arcs');
    expect(arcs).toHaveAttribute('aria-hidden', 'true');
    expect(arcs?.querySelectorAll('path.draw-path')).toHaveLength(EVIDENCE.length);
    expect(fanPath(40, 50, 10)).toBe('M 0 50.0 C 22.0 50.0, 18.0 10.0, 40.0 10.0');
  });
});
