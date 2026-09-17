/**
 * The research workspace directory: every destination a signed-in analyst can reach
 * from the primary rail, grouped so the second level is visible rather than hidden.
 * Administration is deliberately absent; it keeps its own separate rail.
 */
export type WorkspaceIconName =
  | 'map'
  | 'research'
  | 'reports'
  | 'subscriptions'
  | 'geolocation'
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
        to: '/subscriptions',
        label: 'Subscriptions',
        description:
          'Follow a topic, conflict, disaster or area on a schedule, and read the saved updates.',
        icon: 'subscriptions',
      },
      {
        to: '/direction',
        label: 'Plans & areas',
        description: 'Reusable geographic areas and structured research questions.',
        icon: 'plans',
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
    title: 'Standing desks',
    items: [
      {
        to: '/trackers',
        label: 'Live monitor',
        description:
          'Daily briefing, conflicts, disasters and the aviation, maritime, space, cyber, social and public figure boards.',
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
        description: 'Threat actors, exploited vulnerabilities and collected cyber reporting.',
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
    title: 'Directory',
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

/** The specialist monitoring modules listed on the live monitor. */
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
    to: '/trackers/cyber',
    label: 'Cyber',
    description: 'Outage signals, ransomware claims and newly exploited vulnerabilities.',
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

/** True when `pathname` is the destination or one of its child routes. */
export function isWorkspacePath(to: string, pathname: string): boolean {
  if (to === '/') return pathname === '/';
  return pathname === to || pathname.startsWith(`${to}/`);
}
