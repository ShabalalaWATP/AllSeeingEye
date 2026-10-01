/** Pure helpers for the evaluation page. Figures are structural checks, never accuracy. */
import type { StatusTone } from '@/components/admin/StatusPill';
import type { EvaluationRun, EvaluationStopReason } from '@/lib/api/evaluations';
import type { LlmProfile } from '@/lib/api/llm';

/** Expected calls before starting: selected cases multiplied by the usual calls per case. */
export function estimateCalls(selected: number, callsPerCase: number): number {
  return Math.max(0, selected) * Math.max(0, callsPerCase);
}

/** The suggested call cap matches the estimate, within the server's bounds. */
export function suggestedCallCap(selected: number, callsPerCase: number, maximum: number): number {
  return Math.min(maximum, Math.max(1, estimateCalls(selected, callsPerCase)));
}

/** A whole number from one to the maximum, or null when the text is not one. */
export function parseCallCap(text: string, maximum: number): number | null {
  if (!/^\d{1,4}$/.test(text.trim())) return null;
  const value = Number(text.trim());
  return value >= 1 && value <= maximum ? value : null;
}

/** Only connections configured for assessment can draft the evaluation reports. */
export function assessmentProfiles(profiles: readonly LlmProfile[]): LlmProfile[] {
  return profiles.filter((profile) => profile.roles.includes('assessment'));
}

const STOP_REASONS: Record<EvaluationStopReason, string> = {
  call_cap: 'Stopped at the call cap',
  allowance_limit: 'Stopped by an AI allowance policy',
  connection_changed: 'Stopped because the AI connection changed',
  access_revoked: 'Stopped because administrator access ended',
  interrupted: 'Interrupted before it finished',
  failed: 'Stopped after an unexpected error',
};

export function describeRun(run: EvaluationRun): { tone: StatusTone; label: string } {
  if (run.status === 'running') {
    return { tone: 'info', label: run.cancel_requested ? 'Cancelling' : 'Running' };
  }
  if (run.status === 'completed') return { tone: 'good', label: 'Completed' };
  if (run.status === 'cancelled') return { tone: 'neutral', label: 'Cancelled' };
  return {
    tone: 'warning',
    label: run.stop_reason === null ? 'Stopped' : STOP_REASONS[run.stop_reason],
  };
}

/** Readable names for the deterministic checks the server reports for each case. */
export const CHECK_LABELS: Readonly<Record<string, string>> = {
  final_citation_reference_validity: 'Final citation labels that resolve',
  raw_citation_reference_validity: 'Raw citation labels that resolve',
  required_evidence_selected_recall: 'Required evidence selected',
  required_evidence_cited_recall: 'Required evidence cited',
  counterevidence_selected_recall: 'Counterevidence selected',
  counterevidence_referenced_any_role_recall: 'Counterevidence referenced',
  statement_fields: 'Statement fields',
  uncited_statement_fields: 'Uncited statement fields',
  raw_report_json_parse_failures: 'Unparseable report answers',
  validation_errors: 'Validator errors',
  validation_warnings: 'Validator warnings',
  expected_declared_organisation_groups_match: 'Declared organisation groups as expected',
};

/** Ratios are shown as shares, null as not applicable, and booleans as yes or no. */
export function formatCheck(value: number | boolean | null | undefined, ratio: boolean): string {
  if (value === null || value === undefined) return 'Not applicable';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return ratio ? `${Math.round(value * 100)}%` : String(value);
}

export function isRatioCheck(name: string): boolean {
  return name.endsWith('_validity') || name.endsWith('_recall');
}

export function formatTokens(value: number | null): string {
  return value === null ? 'Not reported' : value.toLocaleString('en-GB');
}
