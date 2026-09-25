/**
 * The research workspace directory: every destination a signed-in analyst can reach
 * from the primary rail, grouped so the second level is visible rather than hidden.
 * Administration is deliberately absent; it keeps its own separate rail.
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

/** The hub for standing watches; each watch page below it keeps its own entry too. */
export const watchesHub: WorkspaceDestination = {
  to: '/watches',
  label: 'Watches',
  description:
    'Everything you and your teams watch in one place: subscriptions, alert rules, area watches, plans, briefs and annotation monitors.',
  icon: 'watches',
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
      },
      {
        to: '/research/jobs',
        label: 'Research progress',
        description:
          'Queued, running and finished research, with partial sections and links to completed reports.',
        icon: 'progress',
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
  {
    title: 'Standing watches',
    items: [
      watchesHub,
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
  },
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
    title: 'Collaboration',
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

/** Every rail destination in reading order, for search and preview listings. */
export function workspaceDestinations(): readonly WorkspaceDestination[] {
  return [workspaceHome, ...workspaceSections.flatMap((section) => section.items)];
}

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
