/**
 * Curves fanning out from the middle of an SVG's left edge to the vertical centre of
 * each item in a list beside it. Positions come from offsetTop and offsetHeight, which
 * ignore transforms, so items still flying into place are measured where they land.
 * Measured on mount and on resize only, never per scroll frame.
 */
import { useEffect, useState, type RefObject } from 'react';

interface Fan {
  paths: string[];
  width: number;
  height: number;
}

const EMPTY: Fan = { paths: [], width: 0, height: 0 };

function same(a: Fan, b: Fan): boolean {
  return (
    a.width === b.width &&
    a.height === b.height &&
    a.paths.length === b.paths.length &&
    a.paths.every((path, index) => path === b.paths[index])
  );
}

export function fanPath(width: number, from: number, to: number): string {
  const f = (value: number) => value.toFixed(1);
  return `M 0 ${f(from)} C ${f(width * 0.55)} ${f(from)}, ${f(width * 0.45)} ${f(to)}, ${f(width)} ${f(to)}`;
}

/** `listRef` holds the items as direct children; the SVG sits beside it at the same top. */
export function useFanPaths(
  svgRef: RefObject<SVGSVGElement | null>,
  listRef: RefObject<HTMLElement | null>,
): Fan {
  const [fan, setFan] = useState<Fan>(EMPTY);

  useEffect(() => {
    const svg = svgRef.current;
    const list = listRef.current;
    if (svg === null || list === null) return undefined;
    const measure = () => {
      const width = svg.getBoundingClientRect().width;
      const height = list.offsetHeight;
      const items = [...list.children].filter((item) => item instanceof HTMLElement);
      const top = (item: HTMLElement) =>
        item.offsetParent === list ? item.offsetTop : item.offsetTop - list.offsetTop;
      const paths = items.map((item) =>
        fanPath(width, height / 2, top(item) + item.offsetHeight / 2),
      );
      const next = { paths, width, height };
      setFan((current) => (same(current, next) ? current : next));
    };
    measure();
    if (typeof ResizeObserver !== 'function') return undefined;
    const observer = new ResizeObserver(measure);
    observer.observe(list);
    return () => observer.disconnect();
  }, [svgRef, listRef]);

  return fan;
}
