// Synchronous entry for existing app callers. The public page imports the surface
// directly, so supported workers do not also download the main-thread engine.
// Original component provenance and licence: EvilEyeSurface.tsx and THIRD_PARTY_NOTICES.md.
import type { ComponentProps } from 'react';

import EvilEyeSurface from './EvilEyeSurface';
import { createEyeRenderer } from './evilEyeRenderer';

export default function EvilEye(
  props: Omit<ComponentProps<typeof EvilEyeSurface>, 'createRenderer'>,
) {
  return <EvilEyeSurface {...props} createRenderer={createEyeRenderer} />;
}
