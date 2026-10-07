/**
 * The signed-out product page at /enterprise. It appears only when this installation
 * enables it (ASE_PUBLIC_PRODUCT_PAGE_ENABLED); otherwise the route is not found, so
 * other self-hosted installations never advertise this offer.
 */
import { NotFoundPage } from '@/app/NotFoundPage';
import { useSiteFacts } from '@/lib/useSiteFacts';

import { ProductStory } from './ProductStory';

export default function ProductPage() {
  const site = useSiteFacts();
  if (site.status === 'loading') {
    return <div className="min-h-dvh bg-ground" aria-busy="true" />;
  }
  if (!site.facts.product_page_enabled) return <NotFoundPage />;
  return <ProductStory />;
}
