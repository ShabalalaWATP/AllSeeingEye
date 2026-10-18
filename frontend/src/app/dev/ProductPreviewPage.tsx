/**
 * Development-only preview of the public product story without the installation
 * flag, so the page can be built and checked before an operator enables it. With
 * `?primitives`, it shows each scroll motion primitive on its own instead (KAN-173).
 * Routes under /dev exist only in development builds (see app/router/routes.tsx).
 */
import { useState, type CSSProperties, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router';

import { ProductStory } from '@/features/product/ProductStory';
import { CountUp } from '@/features/product/motion/CountUp';
import { DrawPath } from '@/features/product/motion/DrawPath';
import { Reveal } from '@/features/product/motion/Reveal';
import { ScrollChapter } from '@/features/product/motion/ScrollChapter';
import { useHorizontalPin } from '@/features/product/motion/useHorizontalPin';
import { StoryMotionContext, useStoryMotionSource } from '@/features/product/motion/useStoryMotion';

import '@/features/product/product.css';

const BAR: CSSProperties = {
  height: 6,
  marginTop: '1.5rem',
  background: 'var(--story-ember)',
  transformOrigin: 'left',
  transform: 'scaleX(var(--progress))',
};
const CARD: CSSProperties = {
  width: '18rem',
  minHeight: '10rem',
  padding: '1.2rem',
  border: '1px solid var(--story-line)',
  borderRadius: '1rem',
  background: 'var(--story-surface)',
};
const PANELS = ['One', 'Two', 'Three', 'Four', 'Five', 'Six'];

function Demo({ title, children }: { title: string; children: ReactNode }) {
  return (
    <>
      <p className="story-eyebrow">Primitive</p>
      <h2 className="story-title">{title}</h2>
      {children}
    </>
  );
}

function HorizontalTrackDemo() {
  const { trackRef, viewportRef, index, last, goTo, onProgress, onKeyDown } = useHorizontalPin(
    PANELS.length,
  );
  return (
    <ScrollChapter id="demo-track" label="Horizontal track" length={2} onProgress={onProgress}>
      <Demo title="HorizontalPin: vertical scroll moves a track">
        {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions */}
        <div
          role="region"
          aria-roledescription="carousel"
          aria-label="Demo track"
          // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- Arrow keys move the track.
          tabIndex={0}
          onKeyDown={onKeyDown}
        >
          <p style={{ margin: '1rem 0' }}>
            <button type="button" disabled={index === 0} onClick={() => goTo(index - 1)}>
              Previous
            </button>{' '}
            Panel {index + 1} of {PANELS.length}{' '}
            <button type="button" disabled={index === last} onClick={() => goTo(index + 1)}>
              Next
            </button>
          </p>
          <div ref={viewportRef} style={{ position: 'relative', overflowX: 'auto' }}>
            <div ref={trackRef} style={{ display: 'flex', gap: '1rem', width: 'max-content' }}>
              {PANELS.map((panel) => (
                <div key={panel} style={CARD}>
                  {panel}
                </div>
              ))}
            </div>
          </div>
        </div>
      </Demo>
    </ScrollChapter>
  );
}

function Primitives() {
  const [step, setStep] = useState(0);
  return (
    <main id="story">
      <ScrollChapter
        id="demo-pinned"
        label="Pinned chapter"
        length={1.5}
        steps={4}
        onStep={setStep}
      >
        <Demo title="ScrollChapter, pinned">
          <p className="story-lead">Beat {step + 1} of 4. The bar follows --progress.</p>
          <div style={BAR} />
        </Demo>
      </ScrollChapter>
      <ScrollChapter id="demo-passing" label="Unpinned chapter" length={1} pin={false}>
        <Demo title="ScrollChapter, unpinned">
          <p className="story-lead">Plays while passing through the viewport.</p>
          <div style={BAR} />
        </Demo>
      </ScrollChapter>
      <ScrollChapter id="demo-draw" label="Path drawing" length={1}>
        <Demo title="DrawPath">
          <svg viewBox="0 0 400 120" width="400" height="120" aria-hidden="true">
            <DrawPath
              d="M 10 100 C 120 0, 280 120, 390 20"
              stroke="var(--story-ember)"
              strokeWidth={3}
            />
          </svg>
        </Demo>
      </ScrollChapter>
      <HorizontalTrackDemo />
      <section className="story-chapter" aria-label="Reveal and CountUp">
        <div className="story-stage">
          <Demo title="Reveal variants and CountUp">
            <Reveal className="story-lead">Rise (default)</Reveal>
            <Reveal variant="fade" order={1} className="story-lead">
              Fade
            </Reveal>
            <Reveal variant="mask" order={2} className="story-lead">
              Mask
            </Reveal>
            <p className="story-title">
              <CountUp value={423} suffix="+" />
            </p>
          </Demo>
        </div>
      </section>
    </main>
  );
}

function PrimitivesPreview() {
  const motion = useStoryMotionSource();
  return (
    <StoryMotionContext.Provider value={motion}>
      <div className="product-story" data-motion={motion.still ? 'still' : 'moving'}>
        <p style={{ padding: '1rem' }}>
          <Link to="/dev/product-preview">Back to the product story</Link>
        </p>
        <Primitives />
      </div>
    </StoryMotionContext.Provider>
  );
}

export default function ProductPreviewPage() {
  const [params] = useSearchParams();
  return params.has('primitives') ? <PrimitivesPreview /> : <ProductStory />;
}
