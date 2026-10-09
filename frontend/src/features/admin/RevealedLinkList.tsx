import { LinkReveal } from '@/components/ui/LinkReveal';

import type { RevealedLinks } from './useRevealedLinks';

/** Every revealed one-time link, newest first, each with its own dismiss control. */
export function RevealedLinkList({ links, dismiss }: Pick<RevealedLinks, 'links' | 'dismiss'>) {
  if (links.length === 0) return null;
  return (
    <ul aria-label="Revealed one-time links" className="flex flex-col gap-2">
      {links.map((item) => (
        <li key={item.key}>
          <LinkReveal
            title={item.title}
            link={item.link}
            expiresAt={item.expiresAt}
            onDismiss={() => dismiss(item.key)}
          />
        </li>
      ))}
    </ul>
  );
}
