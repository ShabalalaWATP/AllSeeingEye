import { useEffect } from 'react';

import { setCanonicalUrl, setDocumentMeta } from '@/lib/documentMetadata';

import { OPEN_GRAPH_IMAGE } from './content/assets';
import { PAGE_DESCRIPTION, PAGE_TITLE } from './content/chapters';

/** Only mounted after the installation enables this page; never uses URL query data. */
export function useProductMetadata(): void {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = PAGE_TITLE;
    const canonical = new URL('/enterprise', window.location.origin).href;
    // A 1200 x 630 PNG of the real React Bits brand eye and the page headline, made
    // by `pnpm capture:assets`.
    const image = new URL(OPEN_GRAPH_IMAGE.url, window.location.origin).href;
    const restore = [
      setDocumentMeta('description', PAGE_DESCRIPTION),
      setDocumentMeta('robots', 'index, follow'),
      setCanonicalUrl(canonical),
      ...Object.entries({
        'og:type': 'website',
        'og:site_name': 'The All Seeing Eye',
        'og:title': PAGE_TITLE,
        'og:description': PAGE_DESCRIPTION,
        'og:url': canonical,
        'og:image': image,
        'og:image:type': 'image/png',
        'og:image:width': String(OPEN_GRAPH_IMAGE.width),
        'og:image:height': String(OPEN_GRAPH_IMAGE.height),
        'og:image:alt': OPEN_GRAPH_IMAGE.alt,
        'og:locale': 'en_GB',
      }).map(([key, value]) => setDocumentMeta(key, value, 'property')),
    ];
    return () => {
      document.title = previousTitle;
      for (const reset of restore.reverse()) reset();
    };
  }, []);
}
