/**
 * Travel gestures for the journey: the wheel over the stage, a horizontal swipe on touch and
 * the arrow keys whenever focus is on one of the journey's own controls. The wheel only takes
 * the page scroll while there is somewhere left to travel, so the reader is never trapped.
 */
import { useEffect, type RefObject } from 'react';

import { clampIndex, travelSteps } from './journey';

interface Options {
  count: number;
  index: number;
  onIndex: (index: number) => void;
}

const LINE_HEIGHT = 16;

export function useJourneyTravel(
  stage: RefObject<HTMLElement | null>,
  controls: RefObject<HTMLElement | null>,
  { count, index, onIndex }: Options,
): void {
  useEffect(() => {
    const stageElement = stage.current;
    const controlsElement = controls.current;
    if (stageElement === null) return undefined;

    const move = (steps: number): boolean => {
      const next = clampIndex(index + steps, count);
      if (next === index) return false;
      onIndex(next);
      return true;
    };
    const canMove = (direction: number): boolean =>
      direction > 0 ? index < count - 1 : direction < 0 && index > 0;

    let wheelRun = 0;
    const onWheel = (event: WheelEvent): void => {
      const raw = Math.abs(event.deltaY) >= Math.abs(event.deltaX) ? event.deltaY : event.deltaX;
      if (raw === 0 || !canMove(Math.sign(raw))) return;
      event.preventDefault();
      wheelRun += raw * (event.deltaMode === 1 ? LINE_HEIGHT : 1);
      const { steps, rest } = travelSteps(wheelRun);
      wheelRun = rest;
      if (steps !== 0) move(steps);
    };

    let swipeFrom: number | null = null;
    let swipeRun = 0;
    const onPointerDown = (event: PointerEvent): void => {
      swipeFrom = event.clientX;
      swipeRun = 0;
    };
    const onPointerMove = (event: PointerEvent): void => {
      if (swipeFrom === null) return;
      swipeRun += swipeFrom - event.clientX;
      swipeFrom = event.clientX;
      const { steps, rest } = travelSteps(swipeRun);
      swipeRun = rest;
      if (steps !== 0) move(steps);
    };
    const onPointerUp = (): void => {
      swipeFrom = null;
    };

    const onKeyDown = (event: KeyboardEvent): void => {
      const target = event.target as HTMLElement | null;
      // The range scrubber already moves itself with the arrow keys.
      if (target?.tagName === 'INPUT') return;
      const keys: Record<string, number> = {
        ArrowRight: 1,
        ArrowDown: 1,
        PageDown: 4,
        ArrowLeft: -1,
        ArrowUp: -1,
        PageUp: -4,
      };
      if (event.key === 'Home' || event.key === 'End') {
        event.preventDefault();
        onIndex(event.key === 'Home' ? 0 : Math.max(count - 1, 0));
        return;
      }
      const step = keys[event.key];
      if (step === undefined) return;
      event.preventDefault();
      move(step);
    };

    stageElement.addEventListener('wheel', onWheel, { passive: false });
    stageElement.addEventListener('pointerdown', onPointerDown);
    stageElement.addEventListener('pointermove', onPointerMove);
    stageElement.addEventListener('pointerup', onPointerUp);
    stageElement.addEventListener('pointercancel', onPointerUp);
    stageElement.addEventListener('keydown', onKeyDown);
    controlsElement?.addEventListener('keydown', onKeyDown);
    return () => {
      stageElement.removeEventListener('wheel', onWheel);
      stageElement.removeEventListener('pointerdown', onPointerDown);
      stageElement.removeEventListener('pointermove', onPointerMove);
      stageElement.removeEventListener('pointerup', onPointerUp);
      stageElement.removeEventListener('pointercancel', onPointerUp);
      stageElement.removeEventListener('keydown', onKeyDown);
      controlsElement?.removeEventListener('keydown', onKeyDown);
    };
  }, [stage, controls, count, index, onIndex]);
}
