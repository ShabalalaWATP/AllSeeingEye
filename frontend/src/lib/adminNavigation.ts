/** Shared administration destinations. This directory does not fetch operational data. */
export type AdminIconName =
  | 'overview'
  | 'requests'
  | 'users'
  | 'teams'
  | 'ai'
  | 'evaluations'
  | 'sources'
  | 'quality'
  | 'audit'
  | 'security';

export interface AdminDestination {
  readonly to: string;
  readonly label: string;
  readonly description: string;
  readonly icon: AdminIconName;
  readonly enquiriesOnly?: boolean;
}

export interface AdminSection {
  readonly title: string;
  readonly items: readonly AdminDestination[];
}

export const adminOverview: AdminDestination = {
  to: '/admin',
  label: 'Overview',
  description: 'At-a-glance access, service and oversight status for the whole application.',
  icon: 'overview',
};

export const adminSections: readonly AdminSection[] = [
  {
    title: 'Access and teams',
    items: [
      {
        to: '/admin/requests',
        label: 'Account requests',
        description: 'Review applications, approve account access and assign an initial role.',
        icon: 'requests',
      },
      {
        to: '/admin/enquiries',
        label: 'Enquiries',
        description: 'Review deployment enquiries, record contact and handle erasure requests.',
        icon: 'requests',
        enquiriesOnly: true,
      },
      {
        to: '/admin/users',
        label: 'Users',
        description: 'Manage account roles, active access and password reset links.',
        icon: 'users',
      },
      {
        to: '/admin/teams',
        label: 'Teams',
        description: 'Create teams, manage membership and archive workspaces.',
        icon: 'teams',
      },
    ],
  },
  {
    title: 'Research services',
    items: [
      {
        to: '/admin/llm',
        label: 'AI connections',
        description:
          'Configure and test models, apply the global connection and manage team overrides.',
        icon: 'ai',
      },
      {
        to: '/admin/evaluations',
        label: 'Evaluations',
        description:
          'Run selected synthetic cases against a saved connection, with a call cap and estimate.',
        icon: 'evaluations',
      },
      {
        to: '/admin/sources',
        label: 'Sources',
        description: 'Inspect collector health, review polling failures and reset failed sources.',
        icon: 'sources',
      },
      {
        to: '/admin/catalogue',
        label: 'Catalogue',
        description:
          'Every feed, research capability, camera index, map layer and dataset this deployment uses.',
        icon: 'sources',
      },
      {
        to: '/admin/quality',
        label: 'Research quality',
        description:
          'Counts of saved report outcomes and report jobs by template, depth and model connection.',
        icon: 'quality',
      },
    ],
  },
  {
    title: 'Oversight and security',
    items: [
      {
        to: '/admin/audit',
        label: 'Audit log',
        description: 'Review recorded administrative actions and who performed them.',
        icon: 'audit',
      },
      {
        to: '/admin/security',
        label: 'Security',
        description:
          'Set up or manage authenticator protection for your own administrator account.',
        icon: 'security',
      },
    ],
  },
];

/** The section and destination for a pathname, used for breadcrumbs and page context. */
export function adminLocation(
  pathname: string,
): { section: string | null; page: AdminDestination } | null {
  const path = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
  if (path === adminOverview.to) return { section: null, page: adminOverview };
  for (const section of adminSections) {
    const page = section.items.find((item) => path === item.to || path.startsWith(`${item.to}/`));
    if (page !== undefined) return { section: section.title, page };
  }
  return null;
}
