/**
 * The public product story: header, eleven scroll chapters and a footer. Rendered
 * outside the app shell and account themes, on its own fixed dark palette.
 */
import { Link } from 'react-router';
import { PolicyLinks } from '@/components/privacy/PolicyLinks';

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
import { useProductMetadata } from './useProductMetadata';
import { useProductContactNavigation } from './useProductContactNavigation';
import { StoryMotionContext, useStoryMotionSource } from './motion/useStoryMotion';
import { ProductHeader } from './ProductHeader';

import './product.css';
import './story-hero.css';
import './story-sources.css';
import './story-research.css';
import './story-review.css';
import './story-close.css';

export function ProductStory({ enquiriesEnabled = false }: { enquiriesEnabled?: boolean }) {
  const motion = useStoryMotionSource();
  useProductMetadata();
  useProductContactNavigation();
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
          <ContactChapter enquiriesEnabled={enquiriesEnabled} />
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
          <PolicyLinks />
        </footer>
      </div>
    </StoryMotionContext.Provider>
  );
}
