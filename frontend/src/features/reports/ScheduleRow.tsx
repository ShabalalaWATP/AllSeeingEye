import { Link } from 'react-router';
import { Button } from '@/components/ui/Button';
import { Td } from '@/components/ui/Table';
import type { Schedule } from '@/lib/api/schedules';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { formatUtc } from '@/lib/format';
import { describeCadence } from './ScheduleTiming';

export function ScheduleRow({
  item,
  workspaces,
  productTitle,
  busy,
  onToggle,
  onRemove,
  onEdit,
}: {
  item: Schedule;
  workspaces: Workspaces;
  productTitle: string;
  busy: boolean;
  onToggle: (item: Schedule) => void;
  onRemove: (id: string) => void;
  onEdit: (item: Schedule) => void;
}) {
  return (
    <tr className={item.enabled ? '' : 'opacity-60'}>
      <Td className="font-medium">
        {item.name}
        <div className="text-xs text-muted">{workspaces.label(item.team_id)}</div>
        {(item.notify_on_change || item.avoid_repetition) && (
          <p className="mt-2 text-xs font-normal text-muted">
            {item.last_change_summary ?? 'Comparison details will appear here when available.'}
          </p>
        )}
        {item.last_change?.status === 'unchanged' && (
          <p className="mt-2 text-xs text-muted">
            No material change identified in the latest comparison.
          </p>
        )}
        {item.last_change?.previous_report_id && (
          <Link
            className="mt-1 block text-xs font-normal underline"
            to={`/reports/${item.last_change.previous_report_id}`}
          >
            Previous update
          </Link>
        )}
        {item.question && (
          <details className="mt-2 text-xs font-normal">
            <summary className="cursor-pointer">Saved question</summary>
            <p className="mt-2 whitespace-pre-wrap">{item.question}</p>
            <p className="mt-1 text-muted">
              {item.research_mode
                ? `${({ quick: 'Basic', detailed: 'Deep', advanced: 'Advanced' } as const)[item.research_mode]} research, ${item.research_languages.join(', ')}, ${item.research_focus}`
                : 'Existing live evidence'}
            </p>
            {item.conflict_id && <p className="mt-1 text-muted">Conflict: {item.conflict_id}</p>}
            {item.hazard && <p className="mt-1 text-muted">Disaster: {item.hazard}</p>}
            {item.research_area && <p className="mt-1 text-muted">Fixed area boundary</p>}
            {item.research_subject && <p className="mt-1 text-muted">{item.research_subject}</p>}
            <p className="mt-1 text-muted">
              {item.window_hours
                ? item.window_hours % 24 === 0
                  ? `${item.window_hours / 24} days of lookback`
                  : `${item.window_hours} hours of lookback`
                : 'Search period matches update frequency'}
              {item.research_web_search ? ' · Fresh web search included' : ''}
              {item.research_source_ids !== null
                ? ` · ${item.research_source_ids.length} selected sources`
                : ' · All supported sources'}
            </p>
          </details>
        )}
      </Td>
      <Td className="font-mono text-xs text-muted">
        {productTitle}
        {item.country_isos.length > 0
          ? ` · ${item.country_isos.join(', ')}`
          : item.country_iso === null
            ? ''
            : ` · ${item.country_iso}`}
      </Td>
      <Td className="text-xs">{describeCadence(item)}</Td>
      <Td className="font-mono text-xs text-muted">
        {item.enabled ? formatUtc(item.next_run_at) : 'Paused'}
      </Td>
      <Td className="text-xs">
        {item.last_error !== null && <p className="mb-2 text-critical">{item.last_error}</p>}
        {item.last_report_id !== null ? (
          <Link to={`/reports/${item.last_report_id}`} className="hover:underline">
            Latest update
          </Link>
        ) : item.last_error === null ? (
          <span className="text-muted">not yet</span>
        ) : null}
        {item.last_run_at && (
          <p className="mt-1 text-xs text-muted">{formatUtc(item.last_run_at)}</p>
        )}
      </Td>
      <Td>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            disabled={!workspaces.canManage(item) || busy}
            onClick={() => onEdit(item)}
          >
            Edit
          </Button>
          <Button
            disabled={!workspaces.canManage(item) || busy}
            variant="secondary"
            onClick={() => onToggle(item)}
          >
            {item.enabled ? 'Pause' : 'Resume'}
          </Button>
          <Button
            disabled={!workspaces.canManage(item) || busy}
            variant="danger"
            onClick={() => onRemove(item.id)}
          >
            Delete
          </Button>
        </div>
      </Td>
    </tr>
  );
}
