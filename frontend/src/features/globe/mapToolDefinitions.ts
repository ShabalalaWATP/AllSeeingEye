import type { ReactElement, ReactNode } from 'react';
import { mapLayerEntries, mapPanelId } from '@/lib/mapLayerDirectory';
import type { ControlIcon } from './MapControlIcon';

export interface PanelProps {
  label: string;
  /** Optional display title; the label remains the input-owner and route identity. */
  title?: string;
  icon: ControlIcon;
  side?: 'left' | 'right';
  children: ReactNode;
  entry?: boolean;
  caption?: string;
  size?: 'medium';
  /** The layer stays lit when its inspector is closed. */
  on?: boolean;
  onOpen?: () => void;
}
export type MapPanel = ReactElement<PanelProps>;
export const DEFAULT_FAVOURITES = ['draw', 'area', 'rf', 'measure'];
export const TOOL_GROUPS = ['Draw and measure', 'Research', 'Radio and terrain', 'Map settings'];

export function toolId(panel: PanelProps): string {
  return mapPanelId(panel.label) ?? panel.label;
}
export function toolGroup(panel: PanelProps): string {
  switch (toolId(panel)) {
    case 'draw':
    case 'measure':
    case 'route':
    case 'workspace':
      return 'Draw and measure';
    case 'area':
      return 'Research';
    case 'rf':
    case 'terrain':
      return 'Radio and terrain';
    default:
      return 'Map settings';
  }
}
export function toolDescription(panel: PanelProps): string {
  return mapLayerEntries().find((entry) => entry.panel === panel.label)?.description ?? panel.label;
}
export function toolCaption(panel: PanelProps): string | undefined {
  return (
    panel.caption ??
    (
      {
        'Map style': 'Style',
        'Event time': 'Time',
        Measure: 'Measure',
        'Route planner': 'Route',
        'RF link calculator': 'RF',
        'Research area': 'Area',
        'Draw on map': 'Draw',
        'Measure distance and area': 'Measure',
      } as Record<string, string>
    )[panel.label]
  );
}
