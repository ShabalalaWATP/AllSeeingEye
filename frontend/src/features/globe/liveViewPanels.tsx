import { ControlPanel } from './GlobeControls';
import { LiveViewsPanel } from './LiveViewsPanel';
import type { useGlobeLiveViews } from './useGlobeLiveViews';
import { useLiveViewLibrary } from './useLiveViewLibrary';

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

export function liveViewPanels(liveViews: LiveViews) {
  return [
    <ControlPanel key="views" label="Saved views" icon="layers" size="medium">
      <SavedViewsTool liveViews={liveViews} />
    </ControlPanel>,
  ];
}
