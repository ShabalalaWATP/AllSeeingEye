import { useSyncExternalStore } from 'react';

export interface AssistantReportSelection {
  id: string;
  version: number;
  title: string;
  dataCutoff: string | null;
}

interface ReportContextSnapshot {
  available: AssistantReportSelection | null;
  launch: { token: number; report: AssistantReportSelection } | null;
}

const listeners = new Set<() => void>();
let snapshot: ReportContextSnapshot = { available: null, launch: null };
let launchToken = 0;

function publish(next: ReportContextSnapshot) {
  snapshot = next;
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** The reader registers the edition actually loaded through its authorised report API. */
export function registerAssistantReportContext(report: AssistantReportSelection) {
  publish({ ...snapshot, available: report });
  return () => {
    if (snapshot.available === report) publish({ ...snapshot, available: null });
  };
}

export function launchAssistantReportQuestion(report: AssistantReportSelection) {
  if (snapshot.available !== report) return;
  publish({ ...snapshot, launch: { token: ++launchToken, report } });
}

export function useAssistantReportContext() {
  return useSyncExternalStore(subscribe, () => snapshot);
}
