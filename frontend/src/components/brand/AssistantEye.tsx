/** The login eye as a small, transparent, bounded animation for the assistant. */
import EvilEye from './EvilEye';
import { usePageVisible, useReducedMotion } from './useMotionPreferences';

export function AssistantEye({ className }: { className?: string }) {
  const reducedMotion = useReducedMotion();
  const visible = usePageVisible();

  return (
    <div aria-hidden="true" className={`h-full w-full ${className ?? ''}`}>
      <EvilEye
        transparent
        scale={0.7}
        maxFps={reducedMotion ? 1 : 24}
        flameSpeed={reducedMotion ? 0 : 1}
        pupilFollow={reducedMotion ? 0 : 1}
        paused={!visible}
      />
    </div>
  );
}
