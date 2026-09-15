import { fetchAuditPage } from '@/lib/api/admin';
import { formatAgo, formatUtc } from '@/lib/format';
import { useNow } from '@/lib/hooks/useNow';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

import { OverviewCard } from './OverviewCard';
import { describeAction } from './overviewSummaries';

const RECENT = 6;
const loadRecentAudit = async () => (await fetchAuditPage(null)).items.slice(0, RECENT);

export function AuditCard({ className = '' }: { className?: string }) {
  const resource = useScopedResource(loadRecentAudit);
  const now = useNow();
  return (
    <OverviewCard
      title="Audit log"
      to="/admin/audit"
      icon="audit"
      resource={resource}
      className={className}
    >
      {(entries) =>
        entries.length === 0 ? (
          <p className="text-sm text-muted">No administrative activity has been recorded yet.</p>
        ) : (
          <ol aria-label="Recent audit activity" className="relative space-y-0.5">
            {entries.map((entry) => (
              <li
                key={entry.id}
                className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-md px-1 py-1.5"
              >
                <span aria-hidden="true" className="size-1.5 rounded-full bg-ember/80" />
                <span className="min-w-0">
                  <span className="block truncate text-sm">{describeAction(entry.action)}</span>
                  <span className="block truncate text-xs text-muted">
                    {entry.subject ?? (entry.actor_user_id === null ? 'System' : 'No subject')}
                  </span>
                </span>
                <time
                  dateTime={entry.at}
                  title={formatUtc(entry.at)}
                  className="font-mono text-[11px] whitespace-nowrap text-muted"
                >
                  {formatAgo(entry.at, now)}
                </time>
              </li>
            ))}
          </ol>
        )
      }
    </OverviewCard>
  );
}
