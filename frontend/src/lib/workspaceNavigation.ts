/**
 * The research workspace directory: the one definition of every destination a signed-in
 * analyst can reach. The desktop rail, the mobile navigation dialog, the command palette,
 * page titles and section tabs all read it, so each destination has one name everywhere.
 *
 * A destination may have children: pages it summarises or owns, shown nested beneath it
 * (Watches over each kind of watch, Research over its progress). Addresses such as
 * /warning, /direction and /trackers are kept for bookmarks; only the labels are shown.
 * Administration is not a research destination; it is added only for administrators and
 * keeps its own separate, guarded workspace.
 */
export type WorkspaceIconName =
  | 'map'
  | 'research'
  | 'progress'
  | 'reports'
  | 'subscriptions'
  | 'geolocation'
  | 'watches'
  | 'plans'
  | 'monitor'
  | 'alerts'
  | 'annotations'
  | 'ukraine'
  | 'cyber'
  | 'economy'
  | 'sources'
  | 'teams'
  | 'layers'
  | 'search'
  | 'admin';

export interface WorkspaceDestination {
  readonly to: string;
  readonly label: string;
  readonly description: string;
  readonly icon: WorkspaceIconName;
  /** Destinations this one summarises or owns, listed beneath it. */
  readonly children?: readonly WorkspaceDestination[];
}

export interface WorkspaceSection {
  readonly title: string;
  readonly items: readonly WorkspaceDestination[];
}

export const workspaceHome: WorkspaceDestination = {
  to: '/',
  label: 'Map',
  description: 'The globe and map: live events, cameras, infrastructure and overlays.',
  icon: 'map',
};

/** Only administrators are offered this entry; the route itself is guarded separately. */
export const administrationDestination: WorkspaceDestination = {
  to: '/admin',
  label: 'Administration',
  description: 'The separate administration workspace.',
  icon: 'admin',
};

/** Help is reached from the account controls and search rather than the rail. */
export const helpDestination: WorkspaceDestination = {
  to: '/help',
  label: 'Help and guide',
  description:
    'The user guide: the core loop from map to research to watches, where each workspace lives, and the Start here steps.',
  icon: 'search',
};

/** The parent of every standing watch; each supported kind is listed beneath it. */
export const watchesHub: WorkspaceDestination = {
  to: '/watches',
  label: 'Watches',
  description:
    'Everything you and your teams watch in one place: subscriptions, alert rules, area watches, plans, briefs and annotation monitors.',
  icon: 'watches',
  children: [
    {
      to: '/subscriptions',
      label: 'Subscriptions',
      description:
        'Follow a topic, conflict, disaster or area on a schedule, and read the saved updates.',
      icon: 'subscriptions',
    },
    {
      to: '/warning',
      label: 'Alerts',
      description:
        'Alerts raised by your rules and monitors, and the alert rules that watch the live feeds and map areas.',
      icon: 'alerts',
    },
    {
      to: '/direction',
      label: 'Plans and areas',
      description:
        'Collection plans with their intelligence requirements, and saved areas of interest to reuse in research.',
      icon: 'plans',
    },
    {
      to: '/annotation-monitors',
      label: 'Annotation monitors',
      description:
        'Watch selected claims, identities or relationships in a saved report version for changes.',
      icon: 'annotations',
    },
  ],
};

export const workspaceSections: readonly WorkspaceSection[] = [
  {
    title: 'Research',
    items: [
      {
        to: '/research',
        label: 'Research',
        description:
          'Ask a question, choose the scope and collect a cited answer. Your saved research lives here.',
        icon: 'research',
        children: [
          {
            to: '/research/jobs',
            label: 'Research progress',
            description:
              'Queued, running and finished research, with partial sections and links to completed reports.',
            icon: 'progress',
          },
        ],
      },
      {
        to: '/geolocation',
        label: 'Geolocation',
        description:
          'Compare photographs, assess possible locations and keep the saved assessments.',
        icon: 'geolocation',
      },
    ],
  },
  { title: 'Watches', items: [watchesHub] },
  {
    title: 'Monitoring',
    items: [
      {
        to: '/trackers',
        label: 'Live monitor',
        description:
          'Daily briefing, conflicts, disasters and the aviation, maritime, space, social and public figure boards.',
        icon: 'monitor',
      },
      {
        to: '/conflicts/ukraine',
        label: 'Ukraine war',
        description: 'Control of terrain, strikes, equipment losses and the war timeline.',
        icon: 'ukraine',
      },
      {
        to: '/cyber',
        label: 'Cyber intelligence',
        description:
          'Threat actors, exploited vulnerabilities, outages, ransomware claims and collected cyber reporting.',
        icon: 'cyber',
      },
      {
        to: '/economy',
        label: 'Economy',
        description: 'Markets, economic signals and the stories behind them.',
        icon: 'economy',
      },
    ],
  },
  {
    title: 'Teams',
    items: [
      {
        to: '/teams',
        label: 'Teams',
        description: 'Shared research, the team board and workspace access.',
        icon: 'teams',
      },
    ],
  },
];

/** A destination's own views, shown as tabs on its pages. */
export interface WorkspaceView {
  readonly to: string;
  readonly label: string;
}

export const researchTabs: readonly WorkspaceView[] = [
  { to: '/research', label: 'New research' },
  { to: '/research/saved', label: 'Saved research' },
  { to: '/research/jobs', label: 'Research progress' },
];

export const subscriptionTabs: readonly WorkspaceView[] = [
  { to: '/subscriptions', label: 'Subscriptions' },
  { to: '/subscriptions/saved', label: 'Saved updates' },
];

export const geolocationTabs: readonly WorkspaceView[] = [
  { to: '/geolocation', label: 'New assessment' },
  { to: '/geolocation/saved', label: 'Saved assessments' },
];

export interface NavigationEntry {
  readonly to: string;
  readonly label: string;
  readonly description: string;
  /** The rail section, or "Pages" for the map and "Administration" for that workspace. */
  readonly group: string;
}

/** Saved work each section keeps, searchable by name though it is a tab, not a rail entry. */
export function savedViews(): readonly NavigationEntry[] {
  return [
    {
      to: '/research/saved',
      label: 'Saved research',
      description: 'Research reports you or your teams have saved.',
      group: 'Research',
    },
    {
      to: '/geolocation/saved',
      label: 'Saved assessments',
      description: 'Saved photo geolocation assessments.',
      group: 'Research',
    },
    {
      to: '/subscriptions/saved',
      label: 'Saved updates',
      description: 'Every saved update your subscriptions have produced.',
      group: 'Watches',
    },
  ];
}

const withChildren = (item: WorkspaceDestination): readonly WorkspaceDestination[] => [
  item,
  ...(item.children ?? []),
];

/** Every rail destination in reading order, children after their parent. */
export function workspaceDestinations(): readonly WorkspaceDestination[] {
  return [
    workspaceHome,
    ...workspaceSections.flatMap((section) => section.items.flatMap(withChildren)),
  ];
}

/**
 * The rail in reading order as flat entries: what the rail, the mobile dialog and the
 * palette's page results all show. Administration is present only for administrators.
 */
export function navigationEntries(options: { admin?: boolean } = {}): readonly NavigationEntry[] {
  const entry = (item: WorkspaceDestination, group: string): NavigationEntry => ({
    to: item.to,
    label: item.label,
    description: item.description,
    group,
  });
  return [
    entry(workspaceHome, 'Pages'),
    ...workspaceSections.flatMap((section) =>
      section.items.flatMap(withChildren).map((item) => entry(item, section.title)),
    ),
    ...(options.admin ? [entry(administrationDestination, 'Administration')] : []),
  ];
}

/**
 * The specialist boards listed on the live monitor. This is the only copy of the list:
 * the live monitor page and the command palette both read it. Cyber is not here; its
 * board is part of the cyber intelligence workspace.
 */
export const trackerModules: readonly WorkspaceDestination[] = [
  {
    to: '/trackers/social',
    label: 'Social',
    description: 'Public posts, hashtags and keyword bursts against hourly activity.',
    icon: 'monitor',
  },
  {
    to: '/trackers/aviation',
    label: 'Aviation',
    description: 'Military and unusual flying against baseline, emergencies, GNSS interference.',
    icon: 'monitor',
  },
  {
    to: '/trackers/maritime',
    label: 'Maritime',
    description: 'Broadcast warnings: exercises, closures, security incidents, GNSS notices.',
    icon: 'monitor',
  },
  {
    to: '/trackers/space',
    label: 'Space',
    description: 'Stations overhead, the launch schedule and the geomagnetic picture.',
    icon: 'monitor',
  },
  {
    to: '/trackers/figures',
    label: 'Public figures',
    description: 'Heads of state and government, placed by public reporting or at their seat.',
    icon: 'monitor',
  },
];

function matchesPath(to: string, pathname: string): boolean {
  if (to === '/') return pathname === '/';
  return pathname === to || pathname.startsWith(`${to}/`);
}

/** The most specific rail destination containing `pathname`, if any. */
export function activeWorkspacePath(pathname: string): string | undefined {
  let active: string | undefined;
  for (const destination of workspaceDestinations()) {
    if (matchesPath(destination.to, pathname) && destination.to.length > (active?.length ?? -1))
      active = destination.to;
  }
  return active;
}

/**
 * True when `to` is the current rail destination. A parent and its child (Research and
 * Research progress) are never both current: the more specific destination wins.
 */
export function isWorkspacePath(to: string, pathname: string): boolean {
  const active = activeWorkspacePath(pathname);
  return active === undefined ? matchesPath(to, pathname) : active === to;
}

/** True when one of `item`'s children is current, so the parent can show where you are. */
export function containsWorkspacePath(item: WorkspaceDestination, pathname: string): boolean {
  return (item.children ?? []).some((child) => isWorkspacePath(child.to, pathname));
}
