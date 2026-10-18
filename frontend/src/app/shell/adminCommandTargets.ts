/**
 * What the palette offers inside administration: the way back to the research workspace,
 * then every administration page under its section. Research destinations are not listed
 * here; leaving administration is one deliberate step.
 */
import { adminOverview, adminSections } from '@/lib/adminNavigation';

import type { CommandTarget } from './commandTargets';

export const RESEARCH_WORKSPACE_LABEL = 'Research workspace';

export function adminCommandTargets(options: {
  researchTo: string;
  enquiries: boolean;
}): readonly CommandTarget[] {
  return [
    {
      id: 'workspace:research',
      label: RESEARCH_WORKSPACE_LABEL,
      group: 'Workspace',
      description: 'Return to the research page you visited last, or the globe.',
      to: options.researchTo,
    },
    {
      id: `admin:${adminOverview.to}`,
      label: adminOverview.label,
      group: 'Administration',
      description: adminOverview.description,
      to: adminOverview.to,
    },
    ...adminSections.flatMap((section) =>
      section.items
        .filter((item) => !item.enquiriesOnly || options.enquiries)
        .map((item) => ({
          id: `admin:${item.to}`,
          label: item.label,
          group: section.title,
          description: item.description,
          to: item.to,
        })),
    ),
  ];
}
