import { useCallback, useMemo } from 'react';

import type { PublicFigure } from '@/lib/api/figures';
import type { ViewMode } from '@/stores/globe';

import type { GlobeEngineHandle } from '../useGlobeEngine';
import { buildFigureLayers } from './figureLayers';
import type { FigureState } from './useFigures';

/** Selecting a figure closes event details; measuring keeps clicks for the tool. */
export function useFigureSelection(
  figures: FigureState,
  picking: boolean,
  close: () => void,
  engine: GlobeEngineHandle,
  mode: ViewMode,
) {
  const selectFigure = figures.select;
  const selectPublicFigure = useCallback(
    (figure: PublicFigure) => {
      if (picking) return;
      close();
      selectFigure(figure);
    },
    [picking, close, selectFigure],
  );
  const focusFigure = useCallback(
    (figure: PublicFigure) => {
      selectPublicFigure(figure);
      if (!picking)
        engine.flyTo({
          center: [figure.placement.longitude, figure.placement.latitude],
          zoom: figure.placement.basis === 'reported_place' ? 8 : 5,
        });
    },
    [selectPublicFigure, picking, engine],
  );
  const figureLayers = useMemo(
    () =>
      buildFigureLayers(
        figures.visible,
        selectPublicFigure,
        figures.selected?.id ?? null,
        mode === 'globe',
      ),
    [figures.visible, figures.selected?.id, selectPublicFigure, mode],
  );
  return { focusFigure, figureLayers };
}
