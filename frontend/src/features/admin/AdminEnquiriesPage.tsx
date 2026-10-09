import { useEffect, useRef, useState } from 'react';

import { AdminPage, EmptyState } from '@/components/admin/AdminPage';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { ENQUIRY_PAGE_SIZE, type EnquiryStatus } from '@/lib/api/enquiries';
import { describeError } from '@/lib/api/errors';
import { useSiteFacts } from '@/lib/useSiteFacts';

import { EnquiryCard } from './EnquiryCard';
import { useAdminEnquiries } from './useAdminEnquiries';

export default function AdminEnquiriesPage() {
  const site = useSiteFacts();
  if (site.status === 'loading') return <LoadingNote label="Loading enquiry settings" />;
  if (!site.facts.enterprise_enquiries_enabled)
    return (
      <AdminPage eyebrow="Administration" title="Page not found">
        <p className="text-sm text-muted">There is nothing at this address.</p>
      </AdminPage>
    );
  return <EnquiriesWorkspace retention={site.facts.enterprise_enquiry_retention_days} />;
}

function EnquiriesWorkspace({ retention }: { retention: number }) {
  const [status, setStatus] = useState<EnquiryStatus>('new');
  const [offset, setOffset] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);
  const resultsHeading = useRef<HTMLHeadingElement>(null);
  const focusAfterPageChange = useRef(false);
  const movePage = (value: number) => {
    focusAfterPageChange.current = true;
    setOffset(value);
  };
  useEffect(() => {
    // Wait for the old subtree and any native modal to close. Until that commit,
    // the stable heading may still be inert and cannot receive browser focus.
    if (focusAfterPageChange.current) {
      focusAfterPageChange.current = false;
      resultsHeading.current?.focus();
    }
  }, [offset]);
  return (
    <AdminPage
      eyebrow="Access and teams"
      title="Enquiries"
      description={`Review private deployment enquiries. Records expire ${retention} days after submission.`}
    >
      <SelectField
        label="Enquiry status"
        value={status}
        options={[
          { value: 'new', label: 'New' },
          { value: 'contacted', label: 'Contacted' },
          { value: 'closed', label: 'Closed' },
        ]}
        onChange={(event) => {
          setStatus(event.target.value as EnquiryStatus);
          setOffset(0);
          setNotice(null);
        }}
      />
      <h2 ref={resultsHeading} tabIndex={-1} className="text-base font-semibold">
        Enquiry results
      </h2>
      {notice && <Alert tone="success">{notice}</Alert>}
      <EnquiryResults
        key={`${status}:${offset}`}
        status={status}
        offset={offset}
        previous={() => movePage(Math.max(0, offset - ENQUIRY_PAGE_SIZE))}
        next={() => movePage(offset + ENQUIRY_PAGE_SIZE)}
        setNotice={setNotice}
      />
    </AdminPage>
  );
}

function EnquiryResults({
  status,
  offset,
  previous,
  next,
  setNotice,
}: {
  status: EnquiryStatus;
  offset: number;
  previous: () => void;
  next: () => void;
  setNotice: (notice: string | null) => void;
}) {
  const state = useAdminEnquiries(status, offset, previous, setNotice);
  return (
    <section aria-label="Enquiry results" aria-busy={state.loading} className="space-y-4">
      <Button
        variant="secondary"
        busy={state.loading}
        disabled={state.busy !== null}
        onClick={state.reload}
      >
        Refresh enquiries
      </Button>
      {state.error !== null && <Alert tone="error">{describeError(state.error)}</Alert>}
      {state.loading && <LoadingNote label="Loading enquiries" />}
      {state.data && (
        <>
          {state.data.items.length === 0 ? (
            <EmptyState title="No enquiries in this status.">
              Choose another status or refresh later.
            </EmptyState>
          ) : (
            <ul className="space-y-4">
              {state.data.items.map((item) => (
                <EnquiryCard
                  key={item.id}
                  item={item}
                  busy={state.busy === item.id}
                  disabled={state.busy !== null || state.loading}
                  change={state.change}
                />
              ))}
            </ul>
          )}
          <nav aria-label="Enquiry pages" className="flex flex-wrap items-center gap-3">
            <Button
              variant="secondary"
              disabled={offset === 0 || state.busy !== null || state.loading}
              onClick={previous}
            >
              Previous page
            </Button>
            <p role="status" className="text-sm text-muted">
              {state.data.total === 0
                ? '0'
                : `${offset + 1} to ${Math.min(offset + state.data.items.length, state.data.total)}`}{' '}
              of {state.data.total}
            </p>
            <Button
              variant="secondary"
              disabled={
                offset + ENQUIRY_PAGE_SIZE >= state.data.total ||
                state.busy !== null ||
                state.loading
              }
              onClick={next}
            >
              Next page
            </Button>
          </nav>
        </>
      )}
    </section>
  );
}
