/** Shared administration destinations. This directory does not fetch operational data. */
export type AdminIconName =
  'overview' | 'requests' | 'users' | 'teams' | 'ai' | 'sources' | 'audit' | 'security';

export interface AdminDestination {
  readonly to: string;
  readonly label: string;
  readonly description: string;
  readonly icon: AdminIconName;
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
        to: '/admin/sources',
        label: 'Sources',
        description: 'Inspect collector health, review polling failures and reset failed sources.',
        icon: 'sources',
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
