/**
 * Development-only preview of the public product story without the installation
 * flag, so the page can be built and checked before an operator enables it.
 */
import { ProductStory } from '@/features/product/ProductStory';

export default function ProductPreviewPage() {
  return <ProductStory />;
}
