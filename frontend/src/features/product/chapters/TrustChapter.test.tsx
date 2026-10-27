import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DATA_MINIMISATION, LIMITS_TEXT, TRUST_LAYERS } from '../content/platform';
import { StoryMotionContext } from '../motion/useStoryMotion';
import { TrustChapter } from './TrustChapter';

function renderStill() {
  return render(
    <StoryMotionContext.Provider value={{ still: true, idle: true }}>
      <div className="product-story" data-motion="still">
        <TrustChapter />
      </div>
    </StoryMotionContext.Provider>,
  );
}

describe('Trust chapter when the story is still', () => {
  it('shows every security layer settled, with its controls', () => {
    renderStill();
    const chapter = screen.getByRole('region', { name: 'Trust and control' });
    expect(chapter).toHaveAttribute('data-mode', 'still');
    expect(chapter.style.getPropertyValue('--progress')).toBe('1.0000');
    for (const layer of TRUST_LAYERS) {
      expect(screen.getByRole('heading', { name: layer.name })).toBeInTheDocument();
      for (const control of layer.controls) expect(screen.getByText(control)).toBeInTheDocument();
    }
  });

  it('states what is kept and the honest limits, plainly', () => {
    renderStill();
    expect(screen.getByText(DATA_MINIMISATION)).toBeInTheDocument();
    expect(DATA_MINIMISATION).toMatch(/never enter the database/);
    for (const limit of LIMITS_TEXT) expect(screen.getByText(limit)).toBeInTheDocument();
    expect(screen.getByText('Practices, not a security certification.')).toBeInTheDocument();
  });

  it('makes no certification, accreditation or penetration test claim', () => {
    const { container } = renderStill();
    expect(container.textContent).not.toMatch(
      /certified|accredit|penetration|pen test|ISO 27001|SOC 2|Cyber Essentials/i,
    );
  });
});
