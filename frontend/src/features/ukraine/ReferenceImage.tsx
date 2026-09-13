import { useEffect, useState } from 'react';

import { apiBlob } from '@/lib/api/client';
import { referenceImagePath, type ReferenceImage as ImageMeta } from '@/lib/api/ukraine';

const objectUrls = new Map<string, Promise<string>>();

/** Fetches a cached image through the session once and shares the object URL across cards. */
export function loadReferenceImage(
  imageId: string,
  fetcher: (path: string) => Promise<Blob> = apiBlob,
): Promise<string> {
  let pending = objectUrls.get(imageId);
  if (!pending) {
    pending = fetcher(referenceImagePath(imageId)).then((blob) => URL.createObjectURL(blob));
    objectUrls.set(imageId, pending);
    pending.catch(() => objectUrls.delete(imageId));
  }
  return pending;
}

/** A licensed Commons image with its credit in the caption; nothing renders until it loads. */
export function ReferenceImage({
  imageId,
  meta,
  alt,
  fetcher,
  className = '',
}: {
  imageId: string;
  meta: ImageMeta | undefined;
  alt: string;
  fetcher?: ((path: string) => Promise<Blob>) | undefined;
  className?: string;
}) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    loadReferenceImage(imageId, fetcher)
      .then((url) => {
        if (active) setSrc(url);
      })
      .catch(() => {
        if (active) setSrc(null);
      });
    return () => {
      active = false;
    };
  }, [imageId, fetcher]);
  if (src === null || meta === undefined) return null;
  return (
    <figure className={`overflow-hidden rounded border border-line bg-surface-2 ${className}`}>
      <img src={src} alt={alt} width={meta.width} height={meta.height} className="w-full" />
      <figcaption className="px-2 py-1 text-[10px] text-muted">
        <a
          href={meta.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline"
        >
          {meta.credit}
        </a>
        , {meta.licence}, via Wikimedia Commons
      </figcaption>
    </figure>
  );
}
