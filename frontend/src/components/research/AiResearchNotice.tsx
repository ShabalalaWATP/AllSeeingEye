import { Link } from 'react-router';

import { useAiResearchReady } from '@/lib/hooks/useAiResearchReady';
import { selectIsAdmin, useAuthStore } from '@/stores/auth';

export const AI_RESEARCH_UNAVAILABLE =
  'AI research is not set up on this installation yet. An administrator needs to connect an AI provider.';

/**
 * Shown before anyone fills in a research form when no AI connection can serve them. Only a
 * definite "not ready" shows it; the form stays usable, and submission still reports errors.
 * Administrators also get a link to the page where the connection is made.
 */
export function AiResearchNotice({
  className = 'rounded-md border border-amber/40 bg-amber/10 px-3 py-2 text-sm text-text',
  linkClassName = 'mt-1 inline-block font-medium text-ember underline underline-offset-4',
  onNavigate,
}: {
  className?: string;
  linkClassName?: string;
  onNavigate?: () => void;
}) {
  const ready = useAiResearchReady();
  const admin = useAuthStore(selectIsAdmin);
  if (ready !== false) return null;
  return (
    <div role="status" className={className}>
      <p>{AI_RESEARCH_UNAVAILABLE}</p>
      {admin && (
        <Link to="/admin/llm" className={linkClassName} onClick={onNavigate}>
          Connect an AI provider
        </Link>
      )}
    </div>
  );
}
