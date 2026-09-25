import { Link } from 'react-router';

import { AdminIcon } from '@/components/admin/AdminIcon';
import { StatusPill } from '@/components/admin/StatusPill';
import { fetchCapabilities } from '@/lib/api/capabilities';
import { fetchLlmConnections, fetchLlmProfiles } from '@/lib/api/llm';
import { fetchMfaStatus } from '@/lib/api/mfa';
import { fetchNavigationCapabilities } from '@/lib/api/navigation';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

import { OverviewCard } from './OverviewCard';
import { setupChecklist, type SetupState, type SetupStep } from './setupChecklist';

const TITLE = 'Setup checklist';

/** The AI state is required; an optional check that fails reads as unknown, not as failed. */
async function loadSetupState(): Promise<SetupState> {
  const optional = <T,>(request: Promise<T>) => request.catch(() => null);
  const [profiles, connections, mfa, capabilities, navigation] = await Promise.all([
    fetchLlmProfiles(),
    fetchLlmConnections(),
    optional(fetchMfaStatus()),
    optional(fetchCapabilities()),
    optional(fetchNavigationCapabilities(new AbortController().signal)),
  ]);
  return {
    profiles,
    connections: connections.items,
    emailRelay: mfa === null ? null : mfa.available_methods.includes('email'),
    osMaps: capabilities?.os_maps ?? null,
    feedsContact: navigation?.available ?? null,
  };
}

/**
 * Open while an essential AI step is missing, folded once only optional steps remain, and
 * absent when everything is done. Nothing is shown before the state has loaded, so a
 * finished installation never flashes a checklist.
 */
export function SetupChecklistCard({ className = '' }: { className?: string }) {
  const resource = useScopedResource(loadSetupState);
  if (resource.error !== null)
    return (
      <OverviewCard
        title={TITLE}
        to="/admin/llm"
        icon="check"
        resource={resource}
        className={className}
      >
        {() => null}
      </OverviewCard>
    );
  if (resource.data === null) return null;
  const checklist = setupChecklist(resource.data);
  if (checklist.allDone) return null;
  const essentials = checklist.steps.filter((step) => step.essential);
  const optional = checklist.steps.filter((step) => !step.essential);
  return (
    <article
      aria-label={TITLE}
      className={`admin-rise min-w-0 rounded-card border bg-surface/70 ${checklist.essentialDone ? 'border-line/80' : 'border-amber/45'} ${className}`}
    >
      <details open={!checklist.essentialDone} className="group/setup px-4 py-4 sm:px-5">
        <summary className="flex min-h-8 cursor-pointer list-none flex-wrap items-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-lg border border-line/80 bg-surface-2 text-ember">
            <AdminIcon name="check" size={16} />
          </span>
          <h2 className="text-sm font-semibold">{TITLE}</h2>
          {checklist.essentialDone ? (
            <StatusPill tone="good">
              Essentials done · {checklist.remainingOptional} optional left
            </StatusPill>
          ) : (
            <StatusPill tone="warning">AI research is not ready</StatusPill>
          )}
          <AdminIcon
            name="expand"
            size={14}
            className="ml-auto text-muted transition-transform group-open/setup:rotate-180"
          />
        </summary>
        <div className="mt-4 grid gap-5 md:grid-cols-2">
          <StepList label="Essential steps" steps={essentials} />
          <StepList label="Optional steps" steps={optional} />
        </div>
      </details>
    </article>
  );
}

function StepList({ label, steps }: { label: string; steps: readonly SetupStep[] }) {
  return (
    <section aria-label={label} className="min-w-0">
      <h3 className="text-xs font-semibold tracking-wide text-muted uppercase">{label}</h3>
      <ol className="mt-2 space-y-3">
        {steps.map((step) => (
          <li key={step.id} className="flex min-w-0 items-start gap-3">
            <StepStatus done={step.done} />
            <div className="min-w-0 text-sm">
              {step.to === undefined ? (
                <p className="font-medium">{step.title}</p>
              ) : (
                <Link to={step.to} className="font-medium text-text underline underline-offset-4">
                  {step.title}
                </Link>
              )}
              <p className="mt-0.5 text-xs leading-5 text-muted">{step.detail}</p>
              {step.setting === undefined ? null : (
                <p className="mt-0.5 text-xs leading-5 text-muted">
                  Server setting: <code className="font-mono text-text">{step.setting}</code>
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function StepStatus({ done }: { done: boolean | null }) {
  if (done === true) return <StatusPill tone="good">Done</StatusPill>;
  if (done === false) return <StatusPill tone="warning">Not done</StatusPill>;
  return <StatusPill tone="neutral">Unknown</StatusPill>;
}
