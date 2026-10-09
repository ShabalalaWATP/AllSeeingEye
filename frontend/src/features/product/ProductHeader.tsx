/**
 * The story's sticky header: brand mark and wordmark, a chapter progress line, the
 * pause control shared with the sign-in screen, and the two calls to action.
 */
import { useEffect, useRef } from 'react';
import { Link } from 'react-router';

import { Wordmark } from '@/components/brand/Wordmark';

import { CHAPTER_LINKS } from './content/chapters';
import { clamp01, subscribeScroll } from './motion/scrollScheduler';
import { ProductBrandMark, ProductMotionToggle } from './ProductMotionControls';

export function ProductHeader() {
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const bar = barRef.current;
    if (bar === null) return undefined;
    return subscribeScroll({
      measure: () => {
        const total = document.documentElement.scrollHeight - window.innerHeight;
        return total > 0 ? clamp01(window.scrollY / total) : 0;
      },
      apply: (progress) => bar.style.setProperty('--page-progress', progress.toFixed(4)),
    });
  }, []);

  return (
    <header className="story-header">
      <a className="story-skip" href="#observe">
        Skip to the story
      </a>
      <a className="story-brand" href="#top" aria-label="The All Seeing Eye, back to top">
        <ProductBrandMark />
        <Wordmark className="story-wordmark" />
      </a>
      <nav className="story-nav" aria-label="Chapters">
        <ol>
          {CHAPTER_LINKS.map((chapter) => (
            <li key={chapter.id}>
              <a href={`#${chapter.id}`}>{chapter.label}</a>
            </li>
          ))}
        </ol>
      </nav>
      <div className="story-header-actions">
        <ProductMotionToggle />
        <Link className="story-link" to="/login">
          Sign in
        </Link>
        <a className="story-button story-button-primary story-button-small" href="#contact">
          Talk to us
        </a>
      </div>
      <div ref={barRef} className="story-progress" aria-hidden="true" />
    </header>
  );
}
