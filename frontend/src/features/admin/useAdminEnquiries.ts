import { useCallback, useEffect, useRef, useState } from 'react';

import { deleteEnquiry, listEnquiries, setEnquiryStatus } from '@/lib/api/enquiries';
import type { EnquiryPage, EnquiryStatus } from '@/lib/api/enquiries';

/** One keyed page owns its requests; navigation aborts and discards late completions. */
export function useAdminEnquiries(
  status: EnquiryStatus,
  offset: number,
  previous: () => void,
  setNotice: (notice: string | null) => void,
) {
  const [data, setData] = useState<EnquiryPage | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const reading = useRef<AbortController | null>(null);
  const action = useRef<AbortController | null>(null);
  const load = useCallback(async () => {
    reading.current?.abort();
    const request = new AbortController();
    reading.current = request;
    try {
      const page = await listEnquiries(status, offset, request.signal);
      if (!request.signal.aborted) {
        setData(page);
        setError(null);
      }
    } catch (caught) {
      if (!request.signal.aborted) setError(caught);
    } finally {
      if (!request.signal.aborted) setLoading(false);
    }
  }, [status, offset]);
  useEffect(() => {
    // Loading starts true. Every state update in load follows the awaited request;
    // the hook rule cannot follow that asynchronous boundary through the callback.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    return () => {
      reading.current?.abort();
      action.current?.abort();
    };
  }, [load]);
  const reload = () => {
    setLoading(true);
    void load();
  };
  const change = async (id: string, next: EnquiryStatus | 'delete') => {
    if (action.current !== null) return;
    const request = new AbortController();
    action.current = request;
    setBusy(id);
    setError(null);
    setNotice(null);
    try {
      if (next === 'delete') await deleteEnquiry(id, request.signal);
      else await setEnquiryStatus(id, next, request.signal);
      if (request.signal.aborted) return;
      setNotice(next === 'delete' ? 'Enquiry permanently deleted.' : `Enquiry marked as ${next}.`);
      if (offset > 0 && data?.items.length === 1) previous();
      else {
        setLoading(true);
        await load();
      }
    } catch (caught) {
      if (!request.signal.aborted) setError(caught);
    } finally {
      if (!request.signal.aborted) {
        action.current = null;
        setBusy(null);
      }
    }
  };
  return { data, error, loading, busy, reload, change };
}
