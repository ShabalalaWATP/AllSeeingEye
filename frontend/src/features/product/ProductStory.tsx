/**
 * The public product story: header, eleven scroll chapters and a footer. Rendered
 * outside the app shell and account themes, on its own fixed dark palette.
 */
import { useEffect } from 'react';
import { Link } from 'react-router';

import { AskChapter } from './chapters/AskChapter';
import { AssessChapter } from './chapters/AssessChapter';
import { CollectChapter } from './chapters/CollectChapter';
import { ContactChapter } from './chapters/ContactChapter';
import { DeployChapter } from './chapters/DeployChapter';
import { HeroChapter } from './chapters/HeroChapter';
import { ObserveChapter } from './chapters/ObserveChapter';
import { ReviewChapter } from './chapters/ReviewChapter';
import { SourcesChapter } from './chapters/SourcesChapter';
import { ToolsChapter } from './chapters/ToolsChapter';
import { TrustChapter } from './chapters/TrustChapter';
import { WorkspacesChapter } from './chapters/WorkspacesChapter';
import { PAGE_DESCRIPTION, PAGE_TITLE } from './content/chapters';
import { StoryMotionContext, useStoryMotionSource } from './motion/useStoryMotion';
import { ProductHeader } from './ProductHeader';

import './product.css';
import './story-hero.css';
import './story-sources.css';
import './story-research.css';
import './story-review.css';
import './story-close.css';

function useDocumentMeta(): void {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = PAGE_TITLE;
    let meta = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    const created = meta === null;
    if (meta === null) {
      meta = document.createElement('meta');
      meta.name = 'description';
      document.head.append(meta);
    }
    const previousDescription = meta.content;
    meta.content = PAGE_DESCRIPTION;
    return () => {
      document.title = previousTitle;
      if (created) meta.remove();
      else meta.content = previousDescription;
    };
  }, []);
}

export function ProductStory() {
  const motion = useStoryMotionSource();
  useDocumentMeta();
  return (
    <StoryMotionContext.Provider value={motion}>
      <div className="product-story" data-motion={motion.still ? 'still' : 'moving'}>
        <ProductHeader />
        <main id="story">
          <HeroChapter />
          <ObserveChapter />
          <ToolsChapter />
          <SourcesChapter />
          <AskChapter />
          <CollectChapter />
          <AssessChapter />
          <ReviewChapter />
          <WorkspacesChapter />
          <TrustChapter />
          <DeployChapter />
          <ContactChapter />
        </main>
        <footer className="story-footer">
          <p>The All Seeing Eye. Self-hosted open-source intelligence.</p>
          <p>
            Globe outlines from Natural Earth (public domain). Scenes, questions and reports on this
            page are illustrative and use no live data.
          </p>
          <nav aria-label="Account">
            <Link to="/login">Sign in</Link>
            <Link to="/request-account">Request access</Link>
          </nav>
        </footer>
      </div>
    </StoryMotionContext.Provider>
  );
}
