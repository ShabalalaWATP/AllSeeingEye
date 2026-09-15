import { Link } from 'react-router';
import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Td } from '@/components/ui/Table';
import type { Schedule } from '@/lib/api/schedules';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { formatUtc } from '@/lib/format';
import { describeCadence } from './ScheduleTiming';
import { SubscriptionHistory } from './SubscriptionHistory';
import { BriefScheduleCopy } from './BriefScheduleCopy';

export function ScheduleRow({
  item,
  workspaces,
  productTitle,
  busy,
  onToggle,
  onRunNow,
  onRemove,
  onEdit,
  onDuplicate,
  onBriefCopied,
}: {
  item: Schedule;
  workspaces: Workspaces;
  productTitle: string;
  busy: boolean;
  onToggle: (item: Schedule) => void;
  onRunNow: (id: string) => void;
  onRemove: (id: string) => void;
  onEdit: (item: Schedule, trigger: HTMLButtonElement) => void;
  onDuplicate: (item: Schedule, trigger: HTMLButtonElement) => void;
  onBriefCopied: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [copyBrief, setCopyBrief] = useState(false);
  const confirm = useRef<HTMLDivElement>(null);
  const removeButton = useRef<HTMLSpanElement>(null);
  const duplicateButton = useRef<HTMLSpanElement>(null);
  const requested = useRef(false);
  useEffect(() => {
    if (confirming) confirm.current?.querySelector('button')?.focus();
    else if (requested.current) removeButton.current?.querySelector('button')?.focus();
  }, [confirming]);
  const cancelRemove = () => {
    setConfirming(false);
  };
  return (
    <>
      <tr className={item.enabled ? '' : 'opacity-60'}>
        <Td className="font-medium">
          {item.name}
          <div className="text-xs text-muted">{workspaces.label(item.team_id)}</div>
          {item.brief_id && item.brief_revision && (
            <Link
              className="mt-1 block text-xs font-normal underline"
              to={`/research?brief=${item.brief_id}&revision=${item.brief_revision}`}
            >
              Research Brief revision {item.brief_revision}
            </Link>
          )}
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
          {item.last_outcome === 'failed' && (
            <p className="mb-2 font-medium text-critical">Latest run failed</p>
          )}
          {item.last_outcome === 'needs_review' && (
            <p className="mb-2 font-medium text-amber">Latest report needs review</p>
          )}
          {item.last_coverage === 'partial' && (
            <p className="mb-2 font-medium text-amber">Partial source coverage</p>
          )}
          {item.last_coverage === 'unknown' && (
            <p className="mb-2 text-muted">Source coverage not recorded</p>
          )}
          {item.last_error !== null && <p className="mb-2 text-critical">{item.last_error}</p>}
          {item.last_report_id !== null ? (
            <Link to={`/reports/${item.last_report_id}`} className="hover:underline">
              {item.last_outcome === 'failed' || item.last_error !== null
                ? 'Last successful update'
                : item.last_outcome === 'needs_review'
                  ? 'Review latest update'
                  : item.last_coverage === 'partial'
                    ? 'Review partial update'
                    : 'Latest update'}
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
              disabled={!workspaces.canManage(item) || busy || !item.enabled}
              onClick={() => onRunNow(item.id)}
            >
              Run now
            </Button>
            <Button
              variant="secondary"
              aria-expanded={showHistory}
              onClick={() => setShowHistory((shown) => !shown)}
            >
              History
            </Button>
            <Button
              variant="secondary"
              disabled={!workspaces.canManage(item) || busy || !!item.brief_id}
              onClick={(event) => onEdit(item, event.currentTarget)}
            >
              Edit
            </Button>
            <span ref={duplicateButton}>
              <Button
                variant="secondary"
                disabled={!workspaces.canManage(item) || busy}
                onClick={(event) => {
                  if (item.brief_id) setCopyBrief(true);
                  else onDuplicate(item, event.currentTarget);
                }}
              >
                Duplicate
              </Button>
            </span>
            <Button
              disabled={!workspaces.canManage(item) || busy}
              variant="secondary"
              onClick={() => onToggle(item)}
            >
              {item.enabled ? 'Pause' : 'Resume'}
            </Button>
            {item.brief_id && (
              <p className="basis-full text-xs text-muted">
                This copies the pinned brief revision and timing. Edit the Research Brief to change
                its questions or sources.
              </p>
            )}
            {confirming ? (
              <div
                ref={confirm}
                role="group"
                aria-label={`Archive ${item.name}`}
                className="space-y-2 text-xs"
              >
                <p>Archive {item.name}? Future runs stop. Existing reports remain available.</p>
                <div className="flex gap-2">
                  <Button
                    disabled={!workspaces.canManage(item) || busy}
                    variant="danger"
                    onClick={() => onRemove(item.id)}
                  >
                    Confirm archive
                  </Button>
                  <Button variant="secondary" disabled={busy} onClick={cancelRemove}>
                    Cancel archiving
                  </Button>
                </div>
              </div>
            ) : (
              <span ref={removeButton}>
                <Button
                  disabled={!workspaces.canManage(item) || busy}
                  variant="danger"
                  onClick={() => {
                    requested.current = true;
                    setConfirming(true);
                  }}
                >
                  Archive
                </Button>
              </span>
            )}
          </div>
        </Td>
      </tr>
      {copyBrief && item.brief_id && (
        <tr>
          <td colSpan={6} className="p-3">
            <BriefScheduleCopy
              source={item}
              onCancel={() => {
                setCopyBrief(false);
                duplicateButton.current?.querySelector('button')?.focus();
              }}
              onCreated={() => {
                setCopyBrief(false);
                duplicateButton.current?.querySelector('button')?.focus();
                onBriefCopied();
              }}
            />
          </td>
        </tr>
      )}
      {showHistory && (
        <tr>
          <td colSpan={6} className="p-3">
            <SubscriptionHistory subscriptionId={item.id} canManage={workspaces.canManage(item)} />
          </td>
        </tr>
      )}
    </>
  );
}
