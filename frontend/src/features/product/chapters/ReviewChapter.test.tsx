import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { EXPORTS, REVIEW_TIMELINE, TEAM_ACCESS_NOTE } from '../content/platform';
import { StoryMotionContext } from '../motion/useStoryMotion';
import { ReviewChapter } from './ReviewChapter';

function renderStill() {
  return render(
    <StoryMotionContext.Provider value={{ still: true, idle: true }}>
      <div className="product-story" data-motion="still">
        <ReviewChapter />
      </div>
    </StoryMotionContext.Provider>,
  );
}

describe('Review chapter when the story is still', () => {
  it('shows the whole timeline in its final position', () => {
    renderStill();
    const chapter = screen.getByRole('region', { name: 'Review' });
    expect(chapter).toHaveAttribute('data-mode', 'still');
    expect(chapter.style.getPropertyValue('--progress')).toBe('1.0000');
    for (const beat of REVIEW_TIMELINE)
      expect(within(chapter).getByRole('heading', { name: beat.title })).toBeInTheDocument();
  });

  it('lists every merged alert channel and export, already in place', () => {
    const { container } = renderStill();
    for (const channel of ['In app', 'Email', 'Webhook', 'Web push', 'Atom feed'])
      expect(screen.getByText(channel)).toBeInTheDocument();
    for (const item of EXPORTS) expect(screen.getByText(item.format)).toBeInTheDocument();
    expect(screen.getByText('GeoJSON / KML')).toBeInTheDocument();
    expect(container.querySelector('.review-exports')).toHaveAttribute('data-shown', 'true');
    expect(container.querySelectorAll('.story-reveal[data-shown="false"]')).toHaveLength(0);
  });

  it('explains personal and team scopes and that access follows membership', () => {
    const { container } = renderStill();
    const sharing = container.querySelector('.review-sharing');
    expect(sharing).toHaveTextContent(TEAM_ACCESS_NOTE);
    expect(within(sharing as HTMLElement).getByText('Personal')).toBeInTheDocument();
    expect(screen.getByText('Visible to you and administrators')).toBeInTheDocument();
    expect(
      screen.getByText('Visible to current team members and administrators'),
    ).toBeInTheDocument();
    expect(container.querySelector('.phone-notch')).toHaveAttribute('aria-hidden', 'true');
  });
});
