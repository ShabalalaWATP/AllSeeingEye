/**
 * The signed-out product page at /enterprise. It appears only when this installation
 * enables the product story or enterprise enquiries; otherwise the route is not
 * found. Enquiry admission can be disabled without removing the product story.
 */
import { NotFoundPage } from '@/app/NotFoundPage';
import { useSiteFacts } from '@/lib/useSiteFacts';

import { ProductStory } from './ProductStory';

export default function ProductPage() {
  const site = useSiteFacts();
  if (site.status === 'loading') {
    return <div className="min-h-dvh bg-ground" aria-busy="true" />;
  }
  if (!site.facts.product_page_enabled && !site.facts.enterprise_enquiries_enabled)
    return <NotFoundPage />;
  return <ProductStory enquiriesEnabled={site.facts.enterprise_enquiries_enabled} />;
}
