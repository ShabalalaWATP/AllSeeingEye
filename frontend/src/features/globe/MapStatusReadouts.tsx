import { CoordinateReadout } from './CoordinateReadout';
import { RfMapReadout } from './RfMapReadout';
import { WorldClocks } from './WorldClocks';
import { ReplayBanner } from './replay/ReplayBanner';
import { DailyImageryAttribution } from './imagery/DailyImageryAttribution';
import type { useMapWorkspaceTools } from './useMapWorkspaceTools';
import type { GlobeEngineHandle } from './useGlobeEngine';

/** Passive status stays separate from interactive layer controls and inspectors. */
export function MapStatusReadouts({
  tools,
  engine,
  supported,
  opsRoom,
  bng,
}: {
  tools: ReturnType<typeof useMapWorkspaceTools>;
  engine: GlobeEngineHandle;
  supported: boolean;
  opsRoom: boolean;
  bng: boolean;
}) {
  return (
    <>
      <WorldClocks />
      <ReplayBanner />
      <DailyImageryAttribution />
      {!opsRoom && !tools.picking && (
        <RfMapReadout analysis={tools.rf.analysis} estimate={tools.rf.estimate} />
      )}
      {supported && !opsRoom && !tools.picking && <CoordinateReadout engine={engine} bng={bng} />}
    </>
  );
}
