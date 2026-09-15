import { describe, expect, it } from 'vitest';

import { adminLocation, adminOverview, adminSections } from './adminNavigation';

describe('administration navigation directory', () => {
  it('resolves the overview with and without a trailing slash', () => {
    expect(adminLocation('/admin')).toEqual({ section: null, page: adminOverview });
    expect(adminLocation('/admin/')).toEqual({ section: null, page: adminOverview });
  });

  it('resolves each destination and nested paths to their section', () => {
    for (const section of adminSections) {
      for (const item of section.items) {
        expect(adminLocation(item.to)).toEqual({ section: section.title, page: item });
        expect(adminLocation(`${item.to}/detail`)?.page.label).toBe(item.label);
      }
    }
  });

  it('does not match unrelated or prefix-sharing paths', () => {
    expect(adminLocation('/')).toBeNull();
    expect(adminLocation('/admin/usersx')).toBeNull();
    expect(adminLocation('/research')).toBeNull();
  });

  it('gives every destination an icon and description', () => {
    const items = [adminOverview, ...adminSections.flatMap((section) => section.items)];
    expect(new Set(items.map((item) => item.to)).size).toBe(items.length);
    for (const item of items) {
      expect(item.icon).not.toBe('');
      expect(item.description.length).toBeGreaterThan(10);
    }
  });
});
