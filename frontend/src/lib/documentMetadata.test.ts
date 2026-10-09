import { renderHook } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';

import { useProductMetadata } from '@/features/product/useProductMetadata';

import { setCanonicalUrl, setDocumentMeta } from './documentMetadata';

const created: Element[] = [];
afterEach(() => {
  for (const node of created.splice(0)) node.remove();
});

it('restores pre-existing metadata and canonical values after the product unmounts', () => {
  const description = document.createElement('meta');
  description.name = 'description';
  description.content = 'Installation description';
  const robots = document.createElement('meta');
  robots.name = 'robots';
  robots.content = 'noindex, follow';
  const canonical = document.createElement('link');
  canonical.rel = 'canonical';
  canonical.setAttribute('href', '/previous');
  document.head.append(description, robots, canonical);
  created.push(description, robots, canonical);
  const title = document.title;
  const { unmount } = renderHook(() => useProductMetadata());
  expect(description.content).not.toBe('Installation description');
  unmount();
  expect(description.content).toBe('Installation description');
  expect(robots.content).toBe('noindex, follow');
  expect(canonical.getAttribute('href')).toBe('/previous');
  expect(document.title).toBe(title);
});

it('restores missing attributes on existing head nodes', () => {
  const meta = document.createElement('meta');
  meta.name = 'robots';
  const link = document.createElement('link');
  link.rel = 'canonical';
  document.head.append(meta, link);
  created.push(meta, link);
  const restoreMeta = setDocumentMeta('robots', 'noindex');
  const restoreLink = setCanonicalUrl('https://example.test/enterprise');
  restoreMeta();
  restoreLink();
  expect(meta.hasAttribute('content')).toBe(false);
  expect(link.hasAttribute('href')).toBe(false);
});
