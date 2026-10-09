import { useEffect } from 'react';

import { setCanonicalUrl, setDocumentMeta } from '@/lib/documentMetadata';

import { PAGE_DESCRIPTION, PAGE_TITLE } from './content/chapters';

/** Only mounted after the installation enables this page; never uses URL query data. */
export function useProductMetadata(): void {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = PAGE_TITLE;
    const canonical = new URL('/enterprise', window.location.origin).href;
    // This PNG is the existing 512 x 512 capture of the original React Bits brand eye.
    const image = new URL('/brand/eye-512.png', window.location.origin).href;
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
        'og:image:width': '512',
        'og:image:height': '512',
        'og:image:alt': 'The All Seeing Eye brand mark, a glowing eye.',
        'og:locale': 'en_GB',
      }).map(([key, value]) => setDocumentMeta(key, value, 'property')),
    ];
    return () => {
      document.title = previousTitle;
      for (const reset of restore.reverse()) reset();
    };
  }, []);
}
