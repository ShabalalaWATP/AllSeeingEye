import type { SecFilingChoice, SecFilingsPage } from '@/lib/api/secFilings';
import type { ResearchInputReceipt } from '@/lib/api/researchInputs';
export function secChoice(overrides: Partial<SecFilingChoice> = {}): SecFilingChoice {
  return {
    selection_id: '10000000-0000-4000-8000-000000000001',
    cik: '0000320193',
    accession: '0000320193-26-000001',
    primary_document: 'filing.htm',
    form: '10-K',
    filing_date: '2026-01-01',
    company_name: 'Example company',
    expires_at: new Date(Date.now() + 15 * 60000).toISOString(),
    ...overrides,
  };
}
export function secPage(overrides: Partial<SecFilingsPage> = {}): SecFilingsPage {
  return {
    items: [secChoice()],
    archive_page: 0,
    archive_pages: 1,
    offset: 0,
    next_offset: null,
    limitations: [
      'Recent submissions are one bounded SEC file, not a complete historical inventory.',
    ],
    ...overrides,
  };
}
export function secReceipt(overrides: Partial<ResearchInputReceipt> = {}): ResearchInputReceipt {
  return {
    id: '20000000-0000-4000-8000-000000000002',
    filename: 'filing.htm',
    media_type: 'text/html',
    sha256: 'a'.repeat(64),
    imported_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 15 * 60000).toISOString(),
    event_count: 3,
    extracted_characters: 400,
    preview: '<script>Filing statement, unverified.</script>',
    limitations: ['Tables may lose layout during text extraction.'],
    previews: [],
    ...overrides,
  };
}
