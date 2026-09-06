import { useCallback, useState } from 'react';

import {
  fetchReportSearchStatus,
  indexSavedReports,
  searchSavedReports,
} from '@/lib/api/reportSearch';
import type { ReportSearchResult } from '@/lib/api/reportSearch';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { scopedMutation } from '@/lib/workspaceAccess';

export function useReportSearch() {
  const status = useScopedResource(fetchReportSearchStatus);
  const reload = status.reload;
  const [draft, setDraft] = useState({ key: status.key, query: '' });
  const [found, setFound] = useState<{
    key: string;
    query: string;
    value: ReportSearchResult;
  } | null>(null);
  const query = draft.key === status.key ? draft.query : '';
  const setQuery = (value: string) => setDraft({ key: status.key, query: value });
  const results = found?.key === status.key ? found.value : null;
  const submittedQuery = found?.key === status.key ? found.query : '';
  const search = useAsyncAction(
    useCallback(async () => {
      setFound(null);
      const value = await scopedMutation(() =>
        searchSavedReports({ query: query.trim(), limit: 10 }),
      );
      setFound({ key: status.key, query: query.trim(), value });
      await reload();
    }, [query, reload, status.key]),
  );
  const index = useAsyncAction(
    useCallback(async () => {
      await scopedMutation(indexSavedReports);
      setFound(null);
      await reload();
    }, [reload]),
  );
  return { status, query, setQuery, submittedQuery, results, search, index };
}
