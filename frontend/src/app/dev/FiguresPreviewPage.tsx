/**
 * Development-only page (registered when import.meta.env.DEV) that frames the public
 * figures tracker board, map panel and inspector with fixture data and three portraits
 * from the packaged roster, so the layout can be checked without an account. Nothing here
 * reaches the API with a credential.
 */
import { useState } from 'react';

import { LeftRail } from '@/app/shell/LeftRail';
import { countryOptions, matchesCountries } from '@/components/ui/CountryChips';
import { TopBar } from '@/app/shell/TopBar';
import { FigureInspector } from '@/features/globe/figures/FigureInspector';
import { FigurePanel } from '@/features/globe/figures/FigurePanel';
import type { FigureState } from '@/features/globe/figures/useFigures';
import { FiguresBoard } from '@/features/trackers/FiguresPage';
import type { FigureBoard, PublicFigure } from '@/lib/api/figures';
import { figureBoard } from '@/test/fixtures.figures';

import portraits from './figurePortraits.json';

const board: FigureBoard = {
  ...figureBoard,
  figures: figureBoard.figures.map((figure) => ({
    ...figure,
    portrait: (portraits as Record<string, PublicFigure['portrait']>)[figure.id] ?? null,
  })),
};

function usePreviewState(): FigureState {
  const [enabled, setEnabled] = useState(true);
  const [query, setQuery] = useState('');
  const [reportedOnly, setReportedOnly] = useState(false);
  const [countries, setCountries] = useState<ReadonlySet<string>>(new Set());
  const [selected, setSelected] = useState<PublicFigure | null>(board.figures[0] ?? null);
  const term = query.trim().toLocaleLowerCase('en-GB');
  const visible = enabled
    ? board.figures.filter(
        (figure) =>
          `${figure.name} ${figure.office}`.toLocaleLowerCase('en-GB').includes(term) &&
          matchesCountries(figure, countries) &&
          (!reportedOnly || figure.placement.basis !== 'seat'),
      )
    : [];
  return {
    enabled,
    setEnabled,
    board: enabled ? board : null,
    loading: false,
    error: null,
    query,
    setQuery,
    reportedOnly,
    setReportedOnly,
    countries,
    countryOptions: countryOptions(board.figures),
    toggleCountry: (code: string) =>
      setCountries((old) => {
        const next = new Set(old);
        if (next.has(code)) next.delete(code);
        else next.add(code);
        return next;
      }),
    clearCountries: () => setCountries(new Set()),
    visible,
    selected,
    select: setSelected,
    close: () => setSelected(null),
    refresh: () => undefined,
  };
}

export default function FiguresPreviewPage() {
  const figures = usePreviewState();
  return (
    <div className="flex h-dvh w-full overflow-hidden bg-ground text-text">
      <LeftRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="relative flex min-h-0 flex-1">
          <aside className="w-80 shrink-0 overflow-y-auto border-r border-line bg-surface/60 p-3">
            <FigurePanel figures={figures} onSelect={figures.select} />
          </aside>
          <article className="relative flex min-w-0 flex-1 flex-col gap-5 overflow-y-auto p-6">
            <h1 className="text-xl font-semibold">Public figures</h1>
            <FiguresBoard board={board} />
          </article>
          {figures.selected && (
            <FigureInspector figure={figures.selected} onClose={figures.close} />
          )}
        </main>
      </div>
    </div>
  );
}
