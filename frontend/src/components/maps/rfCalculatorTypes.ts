import type { RfStudyWorkspace } from './RfStudyLibrary';
import type { RfSiteKind, RfSiteNames } from '@/lib/map/rfSites';
import type { RfMapEstimate } from '@/lib/map/rfMap';
import type { Position } from '@/lib/map/geoJsonTypes';
import type { RfDraft } from '@/lib/map/rfDraft';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
export interface RfCalculatorPanelProps {
  siteNames?: RfSiteNames;
  interaction?: 'click' | 'drag';
  onDragSite?: ((kind: RfSiteKind) => void) | undefined;
  onSetSite?: ((kind: RfSiteKind, point: Position, name?: string) => void) | undefined;
  onSwapSites?: (() => void) | undefined;
  onProfilePoint?: ((point: Position | null) => void) | undefined;
  studyWorkspace?: RfStudyWorkspace;

  measuredDistanceKm?: number | undefined;
  origin?: Position | null;
  receiver?: Position | null;
  picking?: 'origin' | 'receiver' | null;
  onPick?: ((point: 'origin' | 'receiver' | null) => void) | undefined;
  onOverlayChange?: (estimate: RfMapEstimate | null) => void;
  overlayVisible?: boolean;
  coverageBubble?: boolean;
  onCoverageBubbleChange?: (value: boolean) => void;
  draft?: RfDraft;
  onDraftChange?: (draft: RfDraft) => void;
  onClearReceiver?: (() => void) | undefined;
  analysis?: RfAnalysis | null;
  onAnalysisChange?: ((value: RfAnalysis | null) => void) | undefined;
}
