import { useEffect, useState } from 'react';

import { loadReferenceImage } from './ReferenceImage';

type Fetcher = ((path: string) => Promise<Blob>) | undefined;

/**
 * The small commander portrait or unit emblem on a chart node. The licence and credit for the
 * same image are shown in full in the detail panel, which is where the node links.
 */
export function ForcePortrait({
  imageId,
  name,
  fetcher,
}: {
  imageId: string;
  name: string;
  fetcher?: Fetcher;
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
  if (src === null) return null;
  return (
    <img
      src={src}
      alt=""
      aria-hidden="true"
      title={`${name}: image credited in the detail panel`}
      className="h-9 w-9 shrink-0 rounded border border-line object-cover"
    />
  );
}
