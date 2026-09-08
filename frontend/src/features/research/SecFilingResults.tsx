import { Button } from '@/components/ui/Button';
import { formatUtc } from '@/lib/format';
import type { SecFilingChoice, SecFilingsPage } from '@/lib/api/secFilings';
export function SecFilingResults({
  page,
  disabled,
  onPage,
  onImport,
}: {
  page: SecFilingsPage;
  disabled: boolean;
  onPage: (archive: number, offset: number) => void;
  onImport: (choice: SecFilingChoice) => void;
}) {
  return (
    <section aria-label="SEC filing discovery results" className="space-y-3">
      <h3 className="font-medium">Filing metadata, documents not imported yet</h3>
      <p className="text-xs text-muted">
        {page.archive_page === 0
          ? 'Recent submissions file'
          : `Older submissions file ${page.archive_page} of ${page.archive_pages}`}
        . This is a bounded page of SEC records. Filing statements are not independently verified.
      </p>
      <ul className="list-disc space-y-1 pl-4 text-xs text-muted">
        {page.limitations.map((value, index) => (
          <li key={index}>{value}</li>
        ))}
      </ul>
      {page.items.length === 0 ? (
        <p role="status" className="text-sm">
          No selectable filings on this page. This does not prove that no filings exist; check the
          coverage notes and available older files.
        </p>
      ) : (
        <ul className="divide-y divide-line">
          {page.items.map((item) => (
            <li key={item.selection_id} className="space-y-2 py-3">
              <h4 className="font-medium">
                {item.company_name} / {item.form}
              </h4>
              <p className="text-sm">
                Filed {item.filing_date}; CIK {item.cik}
              </p>
              <p className="break-all text-xs text-muted">
                Accession {item.accession}; primary document {item.primary_document}
              </p>
              <p className="text-xs text-muted">Selection expires {formatUtc(item.expires_at)}</p>
              <Button
                variant="secondary"
                disabled={disabled}
                aria-label={`Import document ${item.accession}`}
                onClick={() => onImport(item)}
              >
                Import this filing document
              </Button>
            </li>
          ))}
        </ul>
      )}
      <nav aria-label="SEC filing result pages" className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          disabled={disabled || page.offset === 0}
          onClick={() => onPage(page.archive_page, Math.max(0, page.offset - 20))}
        >
          Previous filing results
        </Button>
        <Button
          variant="secondary"
          disabled={disabled || page.next_offset === null}
          onClick={() => {
            if (page.next_offset !== null) onPage(page.archive_page, page.next_offset);
          }}
        >
          Next filing results
        </Button>
        <Button
          variant="secondary"
          disabled={disabled || page.archive_page === 0}
          onClick={() => onPage(page.archive_page - 1, 0)}
        >
          Newer submissions file
        </Button>
        <Button
          variant="secondary"
          disabled={disabled || page.archive_page >= page.archive_pages}
          onClick={() => onPage(page.archive_page + 1, 0)}
        >
          Older submissions file
        </Button>
      </nav>
    </section>
  );
}
