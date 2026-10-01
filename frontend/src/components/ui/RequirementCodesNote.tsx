import { GLOSSARY_PATH, REQUIREMENT_CODES } from '@/lib/glossary';
import type { RequirementCode } from '@/lib/glossary';

/**
 * Expands the requirement codes a screen shows, once, so the codes beside each item stay
 * short. A plain link: it also renders outside the router, in previews and tests.
 */
export function RequirementCodesNote({ codes }: { codes: readonly RequirementCode[] }) {
  if (codes.length === 0) return null;
  return (
    <p className="text-xs leading-5 text-muted">
      {codes.map((code) => `${code}: ${REQUIREMENT_CODES[code]}.`).join(' ')}{' '}
      <a href={GLOSSARY_PATH} className="text-ember underline underline-offset-2">
        Glossary of terms
      </a>
    </p>
  );
}
