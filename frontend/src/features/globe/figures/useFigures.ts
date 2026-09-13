import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react';

import { fetchFigures, type FigureBoard, type PublicFigure } from '@/lib/api/figures';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

const REFRESH_MS = 5 * 60_000;

function matches(figure: PublicFigure, term: string): boolean {
  if (!term) return true;
  return [figure.name, figure.office, figure.country_iso ?? '', figure.organisation ?? '']
    .join(' ')
    .toLocaleLowerCase('en-GB')
    .includes(term);
}

/** The layer is off by default; it loads only for a signed-in identity and forgets on change. */
export function useFigures() {
  const authority = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const accessRevision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const scope = `${authority}:${accessRevision}`;
  const anonymous = authority.startsWith('anonymous:');
  const request = useScopedRequest();
  const [enabled, setEnabled] = useState(false);
  const [board, setBoard] = useState<{ scope: string; value: FigureBoard } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [query, setQuery] = useState('');
  const [reportedOnly, setReportedOnly] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || anonymous) return;
    const signal = request();
    let current = true;
    void fetchFigures(signal)
      .then((value) => {
        if (!current || signal.aborted) return;
        setBoard({ scope, value });
        setError(null);
        setLoading(false);
      })
      .catch(() => {
        if (!current || signal.aborted) return;
        setBoard(null);
        setError('Public figures could not be loaded. Retry to reconnect.');
        setLoading(false);
      });
    const timer = setInterval(() => setRevision((value) => value + 1), REFRESH_MS);
    return () => {
      current = false;
      clearInterval(timer);
      request();
    };
  }, [enabled, revision, scope, anonymous, request]);

  const data = board?.scope === scope ? board.value : null;
  const term = query.trim().toLocaleLowerCase('en-GB');
  const visible = useMemo(
    () =>
      enabled && data
        ? data.figures.filter(
            (figure) =>
              matches(figure, term) && (!reportedOnly || figure.placement.basis !== 'seat'),
          )
        : [],
    [enabled, data, term, reportedOnly],
  );
  const selected = useMemo(
    () => visible.find((figure) => figure.id === selectedId) ?? null,
    [visible, selectedId],
  );
  const toggleEnabled = useCallback((value: boolean) => {
    setEnabled(value);
    setLoading(value);
    setError(null);
    if (!value) setSelectedId(null);
  }, []);
  return {
    enabled,
    setEnabled: toggleEnabled,
    board: data,
    loading: !anonymous && enabled && (loading || data === null) && error === null,
    error,
    query,
    setQuery: useCallback((value: string) => setQuery(value.slice(0, 120)), []),
    reportedOnly,
    setReportedOnly,
    visible,
    selected,
    select: useCallback((figure: PublicFigure | null) => setSelectedId(figure?.id ?? null), []),
    close: useCallback(() => setSelectedId(null), []),
    refresh: useCallback(() => {
      setLoading(true);
      setError(null);
      setRevision((value) => value + 1);
    }, []),
  };
}
export type FigureState = ReturnType<typeof useFigures>;
