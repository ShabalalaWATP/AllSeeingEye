/** Shared administration destinations. This directory does not fetch operational data. */
export const adminSections = [
  {
    title: 'Access and teams',
    items: [
      {
        to: '/admin/requests',
        label: 'Account requests',
        description: 'Review applications, approve account access and assign an initial role.',
      },
      {
        to: '/admin/users',
        label: 'Users',
        description: 'Manage account roles, active access and password reset links.',
      },
      {
        to: '/admin/teams',
        label: 'Teams',
        description: 'Create teams, manage membership and archive workspaces.',
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
      },
      {
        to: '/admin/sources',
        label: 'Sources',
        description: 'Inspect collector health, review polling failures and reset failed sources.',
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
      },
      {
        to: '/admin/security',
        label: 'Security',
        description:
          'Set up or manage authenticator protection for your own administrator account.',
      },
    ],
  },
] as const;
