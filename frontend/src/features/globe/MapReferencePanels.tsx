import type { ComponentProps } from 'react';
import { ControlPanel } from './GlobeControls';
import { BaseLayerToolbar } from './BaseLayerToolbar';
import { NationFilter } from './NationFilter';
import { CountryPanel } from './CountryPanel';
import { GeographicPrecisionPanel } from './GeographicPrecisionPanel';
import { BritishGridTool } from './BritishGridTool';
import { CameraPanel } from './cameras/CameraPanel';

/** Direct panel elements allow the rail to maintain one active inspector. */
export function mapReferencePanels(props: {
  base: ComponentProps<typeof BaseLayerToolbar>;
  nation: ComponentProps<typeof NationFilter>;
  country: ComponentProps<typeof CountryPanel> | null;
  precision: ComponentProps<typeof GeographicPrecisionPanel>;
  grid: ComponentProps<typeof BritishGridTool>;
  cameras: ComponentProps<typeof CameraPanel>;
}) {
  return [
    <ControlPanel key="style" side="right" label="Map style" icon="layers">
      <BaseLayerToolbar {...props.base} />
    </ControlPanel>,
    <ControlPanel key="nation" label="Find nation" icon="nation">
      <NationFilter {...props.nation} />
      {props.country && <CountryPanel {...props.country} />}
    </ControlPanel>,
    <ControlPanel key="precision" label="Location precision" icon="precision">
      <GeographicPrecisionPanel {...props.precision} />
    </ControlPanel>,
    <ControlPanel key="grid" side="right" label="British National Grid" icon="grid">
      <BritishGridTool {...props.grid} />
    </ControlPanel>,
    <ControlPanel key="cctv" side="left" label="CCTV" icon="camera">
      <CameraPanel {...props.cameras} />
    </ControlPanel>,
  ];
}
