import { useEffect, useRef, useState } from 'react';
import { downloadSecOriginal, importSecFiling, searchSecFilings } from '@/lib/api/secFilings';
import type { SecFilingChoice, SecFilingsPage, SecFilingsSearch } from '@/lib/api/secFilings';
import type { ResearchInputReceipt } from '@/lib/api/researchInputs';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { saveBinaryFile } from '@/lib/downloadBinary';
import type { ResearchInputProps } from './ResearchInput';
import type { SecSearchDraft } from './SecSearchFields';
const today = () => new Date().toISOString().slice(0, 10);
export function useSecFilingInput({ onChange, onBusyChange }: ResearchInputProps) {
  const [draft, setDraft] = useState<SecSearchDraft>(() => ({
    cik: '',
    since: new Date(Date.now() - 365 * 86400000).toISOString().slice(0, 10),
    until: today(),
  }));
  const [page, setPage] = useState<SecFilingsPage | null>(null);
  const [attached, setAttached] = useState<{
    choice: SecFilingChoice;
    receipt: ResearchInputReceipt;
  } | null>(null);
  const [declarationBusy, setDeclarationBusy] = useState(false);
  const [busy, setBusy] = useState<'search' | 'import' | 'download' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const pending = useRef(false);
  const request = useScopedRequest();
  const callbacks = useRef({ onChange, onBusyChange });
  useEffect(() => {
    callbacks.current = { onChange, onBusyChange };
  }, [onChange, onBusyChange]);
  useEffect(() => {
    callbacks.current.onBusyChange?.(busy !== null || declarationBusy);
    return () => callbacks.current.onBusyChange?.(false);
  }, [busy, declarationBusy]);
  useEffect(
    () => () => {
      callbacks.current.onChange(null);
    },
    [],
  );
  const clear = () => {
    request();
    pending.current = false;
    setBusy(null);
    setAttached(null);
    setPage(null);
    setError(null);
    setNotice(null);
    callbacks.current.onChange(null);
  };
  const edit = (next: SecSearchDraft) => {
    clear();
    setDraft(next);
  };
  useEffect(() => {
    if (!attached) return;
    const remaining = Date.parse(attached.receipt.expires_at) - Date.now();
    const timer = window.setTimeout(
      () => {
        setAttached(null);
        callbacks.current.onChange(null);
        setNotice(
          'This imported filing has expired. Discover and import it again before starting research.',
        );
      },
      Math.max(0, Math.min(remaining, 15 * 60_000)),
    );
    return () => window.clearTimeout(timer);
  }, [attached]);
  const search = async (archivePage = 0, offset = 0) => {
    if (pending.current) return;
    const span = Date.parse(draft.until) - Date.parse(draft.since);
    if (
      !/^[0-9]{1,10}$/.test(draft.cik.trim()) ||
      !Number.isFinite(span) ||
      span < 0 ||
      span > 3660 * 86400000 ||
      draft.since < '1994-01-01' ||
      draft.until > today()
    ) {
      setError(
        'Enter a CIK with 1 to 10 digits and filing dates from 1994 through today, spanning at most ten years.',
      );
      return;
    }
    clear();
    const signal = request();
    pending.current = true;
    setBusy('search');
    const body: SecFilingsSearch = {
      cik: draft.cik.trim(),
      since: draft.since,
      until: draft.until,
      archive_page: archivePage,
      offset,
    };
    try {
      const result = await searchSecFilings(body, signal);
      signal.throwIfAborted();
      setPage(result);
    } catch (caught) {
      if (!signal.aborted) setError(describeError(caught));
    } finally {
      if (!signal.aborted) {
        pending.current = false;
        setBusy(null);
      }
    }
  };
  const importChoice = async (choice: SecFilingChoice) => {
    if (pending.current) return;
    if (Date.parse(choice.expires_at) <= Date.now()) {
      setPage(null);
      setNotice('This filing selection has expired. Run discovery again.');
      return;
    }
    const signal = request();
    pending.current = true;
    setBusy('import');
    setError(null);
    setNotice(null);
    setAttached(null);
    callbacks.current.onChange(null);
    try {
      const receipt = await importSecFiling(choice.selection_id, signal);
      signal.throwIfAborted();
      if (Date.parse(receipt.expires_at) <= Date.now()) {
        setNotice('The imported input has expired. Discover and import the filing again.');
        return;
      }
      setAttached({ choice, receipt });
      callbacks.current.onChange(receipt.id);
    } catch (caught) {
      if (!signal.aborted) setError(describeError(caught));
    } finally {
      if (!signal.aborted) {
        pending.current = false;
        setBusy(null);
      }
    }
  };
  const download = async () => {
    if (pending.current || !attached) return;
    if (Date.parse(attached.choice.expires_at) <= Date.now()) {
      setError(
        'The temporary original has expired. Discover and import the filing again to download it.',
      );
      return;
    }
    const signal = request();
    pending.current = true;
    setBusy('download');
    setError(null);
    try {
      const blob = await downloadSecOriginal(attached.choice.selection_id, signal);
      signal.throwIfAborted();
      saveBinaryFile(`sec-${attached.choice.accession}-${attached.choice.primary_document}`, blob);
    } catch (caught) {
      if (!signal.aborted) setError(describeError(caught));
    } finally {
      if (!signal.aborted) {
        pending.current = false;
        setBusy(null);
      }
    }
  };
  return {
    declarationBusy,
    setDeclarationBusy,
    replaceReceipt: (receipt: ResearchInputReceipt) => {
      if (
        !attached ||
        receipt.parent_input_id !== attached.receipt.id ||
        receipt.sha256 !== attached.receipt.sha256 ||
        Date.parse(receipt.expires_at) <= Date.now()
      )
        return;
      setAttached({ ...attached, receipt });
      callbacks.current.onChange(receipt.id);
    },
    draft,
    edit,
    page,
    attached,
    busy,
    error,
    notice,
    search,
    importChoice,
    download,
    clear,
    cancel: () => {
      request();
      pending.current = false;
      setBusy(null);
      setError(null);
      if (busy !== 'download') {
        setAttached(null);
        setPage(null);
        callbacks.current.onChange(null);
      }
      setNotice('SEC request cancelled.');
    },
  };
}
