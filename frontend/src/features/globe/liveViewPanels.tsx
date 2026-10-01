import { useGlobeStore } from '@/stores/globe';
import { useLiveViewStore } from '@/stores/liveView';
import { ControlPanel } from './GlobeControls';
import { LiveViewsPanel } from './LiveViewsPanel';
import { OpsPlaylistPanel } from './OpsPlaylistPanel';
import type { useGlobeLiveViews } from './useGlobeLiveViews';
import { useLiveViewLibrary } from './useLiveViewLibrary';
import { useOpsPlaylistEditor } from './useOpsPlaylistEditor';

type LiveViews = ReturnType<typeof useGlobeLiveViews>;

/** The library loads only while its panel is open, so the first map paint stays light. */
function SavedViewsTool({ liveViews }: { liveViews: LiveViews }) {
  const library = useLiveViewLibrary();
  return (
    <LiveViewsPanel
      library={library}
      controls={liveViews.controls}
      onOpen={liveViews.opening.openId}
    />
  );
}

function OpsPlaylistTool() {
  const editor = useOpsPlaylistEditor();
  return (
    <OpsPlaylistPanel
      editor={editor}
      onPlay={(id) => {
        useLiveViewStore.getState().startPlaylist(id);
        useGlobeStore.getState().setOpsRoom(true);
      }}
    />
  );
}

export function liveViewPanels(liveViews: LiveViews) {
  return [
    <ControlPanel key="views" label="Saved views" icon="layers" size="medium">
      <SavedViewsTool liveViews={liveViews} />
    </ControlPanel>,
    <ControlPanel key="ops-room" label="Ops room playlist" icon="time" size="medium">
      <OpsPlaylistTool />
    </ControlPanel>,
  ];
}
