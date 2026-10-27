import { describe, expect, it } from 'vitest';

import { adminSections } from '@/lib/adminNavigation';

import { RESEARCH_WORKSPACE_LABEL, adminCommandTargets } from './adminCommandTargets';

describe('administration palette targets', () => {
  it('leads with the way back to the remembered research route', () => {
    const [first] = adminCommandTargets({ researchTo: '/watches', enquiries: false });
    expect(first).toMatchObject({ label: RESEARCH_WORKSPACE_LABEL, to: '/watches' });
  });

  it('lists every administration page under its section, and nothing from research', () => {
    const targets = adminCommandTargets({ researchTo: '/', enquiries: true });
    const pages = targets.slice(1);
    expect(pages.every((target) => target.to.startsWith('/admin'))).toBe(true);
    const items = adminSections.flatMap((section) => section.items);
    expect(pages).toHaveLength(items.length + 1);
    expect(new Set(targets.map((target) => target.id)).size).toBe(targets.length);
    expect(targets.find((target) => target.to === '/admin/users')?.group).toBe('Access and teams');
  });

  it('offers enquiries only where the installation enables them', () => {
    const routes = (enquiries: boolean) =>
      adminCommandTargets({ researchTo: '/', enquiries }).map((target) => target.to);
    expect(routes(false)).not.toContain('/admin/enquiries');
    expect(routes(true)).toContain('/admin/enquiries');
  });
});
