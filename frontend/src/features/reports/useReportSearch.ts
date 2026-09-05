import { useCallback, useState } from 'react';

import {
  fetchReportSearchStatus,
  indexSavedReports,
  searchSavedReports,
} from '@/lib/api/reportSearch';
import type { ReportSearchResult } from '@/lib/api/reportSearch';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useResource } from '@/lib/hooks/useResource';

export function useReportSearch() {
  const status = useResource(fetchReportSearchStatus);
  const reload = status.reload;
  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [results, setResults] = useState<ReportSearchResult | null>(null);
  const search = useAsyncAction(
    useCallback(async () => {
      setResults(null);
      const found = await searchSavedReports({ query: query.trim(), limit: 10 });
      setSubmittedQuery(query.trim());
      setResults(found);
      await reload();
    }, [query, reload]),
  );
  const index = useAsyncAction(
    useCallback(async () => {
      await indexSavedReports();
      setResults(null);
      await reload();
    }, [reload]),
  );
  return { status, query, setQuery, submittedQuery, results, search, index };
}
