/**
 * Curved SVG paths joining pairs of elements inside a stage, measured on mount and on
 * resize only (never per scroll frame). Elements are found by data attributes:
 * `data-from="id"` and `data-to="id"`. Pass a stable `pairs` array (a module
 * constant); an unchanged measurement does not re-render.
 */
import { useEffect, useState, type RefObject } from 'react';

export interface Connector {
  key: string;
  d: string;
}

interface Measured {
  connectors: Connector[];
  width: number;
  height: number;
}

function sameMeasurement(a: Measured, b: Measured): boolean {
  return (
    a.width === b.width &&
    a.height === b.height &&
    a.connectors.length === b.connectors.length &&
    a.connectors.every((connector, index) => connector.d === b.connectors[index]?.d)
  );
}

function curve(box: DOMRect, a: DOMRect, b: DOMRect): string {
  const x1 = a.left - box.left + a.width / 2;
  const y1 = a.top - box.top + a.height / 2;
  const x2 = b.right - box.left;
  const y2 = b.top - box.top + b.height / 2;
  const bend = Math.max(40, Math.abs(x1 - x2) * 0.45);
  const f = (value: number) => value.toFixed(1);
  return `M ${f(x1)} ${f(y1)} C ${f(x1 - bend)} ${f(y1)}, ${f(x2 + bend)} ${f(y2)}, ${f(x2)} ${f(y2)}`;
}

export function useConnectorPaths(
  stageRef: RefObject<HTMLElement | null>,
  pairs: readonly (readonly [string, string])[],
): Measured {
  const [state, setState] = useState<Measured>({ connectors: [], width: 0, height: 0 });

  useEffect(() => {
    const stage = stageRef.current;
    if (stage === null) return undefined;
    const measure = () => {
      const box = stage.getBoundingClientRect();
      const connectors: Connector[] = [];
      for (const [from, to] of pairs) {
        const a = stage.querySelector(`[data-from="${from}"]`)?.getBoundingClientRect();
        const b = stage.querySelector(`[data-to="${to}"]`)?.getBoundingClientRect();
        if (a !== undefined && b !== undefined) {
          connectors.push({ key: `${from}-${to}`, d: curve(box, a, b) });
        }
      }
      const next = { connectors, width: box.width, height: box.height };
      setState((current) => (sameMeasurement(current, next) ? current : next));
    };
    measure();
    if (typeof ResizeObserver !== 'function') return undefined;
    const observer = new ResizeObserver(measure);
    observer.observe(stage);
    return () => observer.disconnect();
  }, [stageRef, pairs]);

  return state;
}
