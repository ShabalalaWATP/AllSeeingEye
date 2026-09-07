export const annotationMonitorHref = (monitorId: string) =>
  `/annotation-monitors/${encodeURIComponent(monitorId)}`;
export const annotationTransitionHref = (monitorId: string, transitionId: string) =>
  `${annotationMonitorHref(monitorId)}/transitions/${encodeURIComponent(transitionId)}`;
