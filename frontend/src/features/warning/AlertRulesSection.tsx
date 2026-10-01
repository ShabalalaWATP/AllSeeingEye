import type { ReactNode, RefObject } from 'react';

import { Alert as Notice, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { Table, Td, Th } from '@/components/ui/Table';
import { windowLabel } from '@/lib/alertRules';
import { describeError } from '@/lib/api/errors';
import type { Indicator } from '@/lib/api/warning';
import type { ConfirmedAction } from '@/lib/hooks/useConfirmedAction';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';

import { RuleDeletion } from './RuleDeletion';
import { RuleBaseline } from './RuleBaseline';
import { RuleFeedback } from './RuleFeedback';

export function describeScope(rule: Indicator): string {
  if (rule.research_area) return `exact shape · ${rule.research_area.sha256.slice(0, 12)}`;
  if (rule.bbox !== null) return `box ${rule.bbox.map((n) => n.toFixed(1)).join(', ')}`;
  if (rule.countries.length > 0) return rule.countries.join(', ');
  return 'worldwide';
}

export function describeRule(rule: Indicator): string {
  if (rule.baseline_ratio != null)
    return `${rule.baseline_ratio} times the ${rule.baseline_days ?? 30}-day hourly mean, at least ${rule.threshold} items`;
  const what = [
    rule.categories.length > 0 ? rule.categories.join('/') : 'any category',
    rule.keywords.length > 0 ? `with ${rule.keywords.join(', ')}` : '',
  ]
    .filter((part) => part !== '')
    .join(' ');
  return `${String(rule.threshold)} or more ${what} in ${windowLabel(rule.window_minutes)}`;
}

/** The saved alert rules, what each watches, whether it runs, and what can be done to it. */
export function AlertRulesSection({
  rules,
  loading,
  error,
  workspaces,
  heading,
  remove,
  toggling,
  onEdit,
  onToggle,
  children,
}: {
  rules: readonly Indicator[] | null;
  loading: boolean;
  error: unknown;
  workspaces: Workspaces;
  heading: RefObject<HTMLHeadingElement | null>;
  remove: ConfirmedAction<Indicator>;
  /** The rule whose pause or resume is being saved, if any. */
  toggling: string | null;
  onEdit: (rule: Indicator) => void;
  onToggle: (rule: Indicator) => void;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3">
      <h2 ref={heading} tabIndex={-1} className="text-base font-semibold">
        Alert rules
      </h2>
      {error === null || error === undefined ? null : (
        <Notice tone="error">{describeError(error)}</Notice>
      )}
      {rules === null ? (
        loading ? (
          <LoadingNote label="Loading alert rules" />
        ) : null
      ) : rules.length === 0 ? (
        <EmptyState
          title="No alert rules yet"
          purpose="An alert rule watches connected feeds and raises an alert when enough matching items arrive within its time window, so you notice activity without checking the map."
          action="Set up your first alert rule with the form below, or choose Watch this area on the map."
        />
      ) : (
        <Table caption="Alert rules">
          <thead>
            <tr>
              <Th>Alert rule</Th>
              <Th>Status</Th>
              <Th>Scope</Th>
              <Th>Rule</Th>
              <Th>Report</Th>
              <Th>
                <span className="sr-only">Actions</span>
              </Th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => {
              const manage = workspaces.canManage(rule);
              return (
                <tr key={rule.id}>
                  <Td className="font-medium">
                    {rule.name}
                    <div className="text-xs text-muted">{workspaces.label(rule.team_id)}</div>
                  </Td>
                  <Td className="text-xs">
                    {rule.enabled ? 'Active' : 'Paused: not evaluated, raises no alerts'}
                  </Td>
                  <Td className="font-mono text-xs text-muted">{describeScope(rule)}</Td>
                  <Td className="text-xs">
                    {describeRule(rule)}
                    <RuleFeedback ruleId={rule.id} />
                    {rule.baseline_ratio != null && <RuleBaseline ruleId={rule.id} />}
                  </Td>
                  <Td className="font-mono text-xs text-muted">{rule.report_template ?? 'none'}</Td>
                  <Td>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="secondary"
                        disabled={!manage}
                        aria-label={`Edit ${rule.name}`}
                        onClick={() => onEdit(rule)}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="secondary"
                        disabled={!manage || toggling !== null}
                        busy={toggling === rule.id}
                        aria-label={`${rule.enabled ? 'Pause' : 'Resume'} ${rule.name}`}
                        onClick={() => onToggle(rule)}
                      >
                        {rule.enabled ? 'Pause' : 'Resume'}
                      </Button>
                      <Button
                        disabled={!manage}
                        variant="danger"
                        aria-haspopup="dialog"
                        aria-label={`Delete ${rule.name}`}
                        onClick={() => remove.ask(rule)}
                      >
                        Delete
                      </Button>
                    </div>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      )}
      <RuleDeletion
        action={remove}
        workspaceLabel={workspaces.label}
        describe={describeRule}
        returnFocus={heading}
      />
      {children}
    </div>
  );
}
