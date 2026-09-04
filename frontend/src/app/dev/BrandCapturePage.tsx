/**
 * Development-only page (registered when import.meta.env.DEV) that shows the Evil
 * Eye at 512 by 512 pixels on the page ground and nothing else, so a headless
 * browser can capture the favicon and static brand assets from the real component.
 */
import EvilEye from '@/components/brand/EvilEye';
import { BRAND_GROUND, BRAND_NAME } from '@/components/brand/tokens';

export default function BrandCapturePage() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-ground">
      <div
        role="img"
        aria-label={BRAND_NAME}
        data-testid="brand-capture"
        style={{ width: 512, height: 512 }}
      >
        <EvilEye pupilFollow={0} backgroundColor={BRAND_GROUND} />
      </div>
    </main>
  );
}
