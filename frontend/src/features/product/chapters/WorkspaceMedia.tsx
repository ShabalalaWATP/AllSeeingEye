/**
 * An illustrative workspace still or loop. Images load lazily at their declared size.
 * Loops are muted, inline and silent, load nothing until they first play, play only
 * while on screen, and stay paused (showing the poster) when the story is still or the
 * tab is hidden.
 */
import { useEffect, useRef } from 'react';

import type { WorkspaceMedia as Media } from '../content/platform';
import { useStoryMotion } from '../motion/useStoryMotion';

// No workspace uses a video yet; Loop stays for the loops planned in KAN-179.
function Loop({ media }: { media: Media }) {
  const { idle } = useStoryMotion();
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = ref.current;
    if (video === null) return undefined;
    const pause = () => video.pause();
    if (idle || typeof IntersectionObserver !== 'function') {
      pause();
      return undefined;
    }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        // Older engines return nothing; a refused play (power saving) keeps the poster.
        void Promise.resolve(video.play()).catch(() => undefined);
      } else pause();
    });
    observer.observe(video);
    return () => {
      observer.disconnect();
      pause();
    };
  }, [idle]);

  return (
    <video
      ref={ref}
      src={media.src}
      poster={media.poster}
      width={media.width}
      height={media.height}
      aria-label={media.alt}
      muted
      playsInline
      loop
      preload="none"
    />
  );
}

export function WorkspaceMedia({ media }: { media: Media }) {
  const label = media.kind === 'video' ? 'Illustrative loop' : 'Illustrative screenshot';
  return (
    <figure className="workspace-media">
      {media.kind === 'video' ? (
        <Loop media={media} />
      ) : (
        <img
          src={media.src}
          alt={media.alt}
          width={media.width}
          height={media.height}
          loading="lazy"
          decoding="async"
        />
      )}
      <figcaption>{label}</figcaption>
    </figure>
  );
}
