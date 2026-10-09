/**
 * The installation's public site facts, shared by the signed-out pages. A successful
 * answer is kept for the page load; a failed request counts as "off" (so an
 * unreachable API never reveals the product page) but is not remembered, so the
 * next visit to a public page asks again.
 */
import { useEffect, useState } from 'react';

import { fetchSiteFacts, type SiteFacts } from './api/site';

export type SiteFactsState = { status: 'loading' } | { status: 'ready'; facts: SiteFacts };

const OFF: SiteFacts = {
  product_page_enabled: false,
  enterprise_enquiries_enabled: false,
  enterprise_enquiry_retention_days: 365,
};
let pending: Promise<SiteFacts> | null = null;

function load(): Promise<SiteFacts> {
  pending ??= fetchSiteFacts().catch(() => {
    pending = null;
    return OFF;
  });
  return pending;
}

/** Tests only: forget a remembered answer between cases. */
export function resetSiteFacts(): void {
  pending = null;
}

export function useSiteFacts(): SiteFactsState {
  const [state, setState] = useState<SiteFactsState>({ status: 'loading' });
  useEffect(() => {
    let live = true;
    void load().then((facts) => {
      if (live) setState({ status: 'ready', facts });
    });
    return () => {
      live = false;
    };
  }, []);
  return state;
}
