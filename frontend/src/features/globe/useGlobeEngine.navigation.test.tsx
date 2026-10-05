import { act, render } from '@testing-library/react';
import { StrictMode, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { ViewMode } from '@/stores/globe';
import type { MapEngine, MapEngineFactory } from './engine/MapEngine';
import { useGlobeEngine } from './useGlobeEngine';
import type { GlobeEngineHandle } from './useGlobeEngine';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));

function fakeEngine() {
  return {
    mount: vi.fn(),
    setProjection: vi.fn(),
    setBaseLayer: vi.fn(),
    setLite: vi.fn(),
    onCursor: vi.fn(() => vi.fn()),
    on: vi.fn(() => vi.fn()),
    destroy: vi.fn(),
    captureImage: vi.fn(),
    setLayers: vi.fn(),
    spin: vi.fn(),
    flyTo: vi.fn(),
    getZoom: vi.fn(() => 2),
    getCamera: vi.fn(() => null),
    restoreCamera: vi.fn(),
    getViewportBounds: vi.fn(() => null),
    fitBounds: vi.fn(),
  } satisfies MapEngine;
}

type Command = (engine: GlobeEngineHandle) => void;
function Child({ engine, command }: { engine: GlobeEngineHandle; command: Command }) {
  useEffect(() => command(engine), [command, engine]);
  return null;
}
function Harness({
  factory,
  command,
  mode = 'globe',
  enabled = true,
}: {
  factory: MapEngineFactory;
  command: Command;
  mode?: ViewMode;
  enabled?: boolean;
}) {
  const container = useRef<HTMLDivElement>(null);
  const engine = useGlobeEngine(container, { enabled, mode, createEngine: factory });
  return (
    <>
      <div ref={container} />
      <Child engine={engine} command={command} />
    </>
  );
}

const firstCamera = { center: [10, 20] as [number, number], zoom: 3, bearing: 0, pitch: 0 };
const lastCamera = { ...firstCamera, center: [30, 40] as [number, number] };
const focus = { center: [50, 60] as [number, number], zoom: 4 };

describe('engine-owned navigation handoff', () => {
  it.each(['camera-camera', 'focus-camera', 'camera-focus', 'focus-focus'] as const)(
    'applies only the latest pre-mount intent for %s',
    (order) => {
      const instance = fakeEngine();
      const command: Command = (engine) => {
        if (order.startsWith('camera')) engine.restoreCamera?.(firstCamera, 'globe');
        else engine.flyTo({ ...focus, zoom: 2 });
        if (order.endsWith('camera')) engine.restoreCamera?.(lastCamera, 'globe');
        else engine.flyTo(focus);
      };
      render(<Harness factory={() => instance} command={command} />);
      if (order.endsWith('camera')) {
        expect(instance.restoreCamera).toHaveBeenCalledExactlyOnceWith(lastCamera);
        expect(instance.flyTo).not.toHaveBeenCalled();
      } else {
        expect(instance.flyTo).toHaveBeenCalledExactlyOnceWith(focus);
        expect(instance.restoreCamera).not.toHaveBeenCalled();
      }
    },
  );

  it('drops a mismatched camera after its authoritative commit and never replays it later', () => {
    const instance = fakeEngine();
    const factory = () => instance;
    const command: Command = (engine) => engine.restoreCamera?.(firstCamera, 'mercator');
    const view = render(<Harness factory={factory} command={command} />);
    expect(instance.restoreCamera).not.toHaveBeenCalled();
    view.rerender(<Harness factory={factory} command={command} mode="map" />);
    expect(instance.setProjection).toHaveBeenLastCalledWith('mercator');
    expect(instance.restoreCamera).not.toHaveBeenCalled();
  });

  it.each(['focus', 'camera'] as const)(
    'lets a newer ready-engine %s supersede a mismatched pending camera',
    (next) => {
      const instance = fakeEngine();
      let handle: GlobeEngineHandle;
      const command: Command = (engine) => {
        handle = engine;
      };
      const factory = () => instance;
      const view = render(<Harness factory={factory} command={command} />);
      act(() => {
        handle.restoreCamera?.(firstCamera, 'mercator');
        if (next === 'focus') handle.flyTo(focus);
        else handle.restoreCamera?.(lastCamera);
      });
      view.rerender(<Harness factory={factory} command={command} mode="map" />);
      if (next === 'focus') {
        expect(instance.flyTo).toHaveBeenCalledExactlyOnceWith(focus);
        expect(instance.restoreCamera).not.toHaveBeenCalled();
      } else {
        expect(instance.restoreCamera).toHaveBeenCalledExactlyOnceWith(lastCamera);
      }
    },
  );

  it.each(['disabled', 'failed'] as const)(
    'discards pending navigation when mount is %s',
    (state) => {
      const first = fakeEngine();
      if (state === 'failed')
        first.mount.mockImplementation(() => {
          throw new Error('no graphics');
        });
      const firstFactory = () => first;
      const command: Command = (engine) => engine.restoreCamera?.(firstCamera, 'globe');
      const view = render(
        <Harness factory={firstFactory} command={command} enabled={state !== 'disabled'} />,
      );
      const second = fakeEngine();
      view.rerender(<Harness factory={() => second} command={command} />);
      expect(second.restoreCamera).not.toHaveBeenCalled();
      expect(first.restoreCamera).not.toHaveBeenCalled();
    },
  );

  it('clears queued navigation on engine replacement and ignores handles after unmount', () => {
    const first = fakeEngine();
    const second = fakeEngine();
    const firstFactory = () => first;
    const secondFactory = () => second;
    let handle: GlobeEngineHandle;
    const command: Command = (engine) => {
      handle = engine;
    };
    const view = render(<Harness factory={firstFactory} command={command} />);
    act(() => {
      handle.restoreCamera?.(firstCamera, 'mercator');
      view.rerender(<Harness factory={secondFactory} command={command} mode="map" />);
    });
    expect(first.destroy).toHaveBeenCalledOnce();
    expect(second.restoreCamera).not.toHaveBeenCalled();
    view.unmount();
    act(() => {
      handle.restoreCamera?.(lastCamera, 'mercator');
      handle.flyTo(focus);
    });
    expect(second.restoreCamera).not.toHaveBeenCalled();
    expect(second.flyTo).not.toHaveBeenCalled();
  });

  it('retains the current child request through StrictMode effect replay', () => {
    const instances: ReturnType<typeof fakeEngine>[] = [];
    const factory = () => {
      const engine = fakeEngine();
      instances.push(engine);
      return engine;
    };
    const command: Command = (engine) => engine.restoreCamera?.(lastCamera, 'globe');
    render(
      <StrictMode>
        <Harness factory={factory} command={command} />
      </StrictMode>,
    );
    expect(instances).toHaveLength(2);
    expect(instances[0]!.destroy).toHaveBeenCalledOnce();
    expect(instances[1]!.restoreCamera).toHaveBeenCalledExactlyOnceWith(lastCamera);
  });

  it.each(['projection', 'navigation'] as const)(
    'keeps a newer intent raised synchronously during %s application',
    (during) => {
      const instance = fakeEngine();
      const factory = () => instance;
      let handle: GlobeEngineHandle;
      let changeMode: (mode: ViewMode) => void;
      const newerRequest = () => {
        handle.restoreCamera?.(lastCamera, 'mercator');
        changeMode('map');
      };
      if (during === 'projection') instance.setProjection.mockImplementationOnce(newerRequest);
      else instance.flyTo.mockImplementationOnce(newerRequest);
      const command: Command = (engine) => {
        handle = engine;
        engine.flyTo(focus);
      };
      function StatefulHarness() {
        const [mode, setMode] = useState<ViewMode>('globe');
        useLayoutEffect(() => {
          changeMode = setMode;
        }, []);
        return <Harness factory={factory} command={command} mode={mode} />;
      }
      render(<StatefulHarness />);
      expect(instance.flyTo).toHaveBeenCalledTimes(during === 'projection' ? 0 : 1);
      expect(instance.restoreCamera).toHaveBeenCalledExactlyOnceWith(lastCamera);
      expect(instance.setProjection).toHaveBeenLastCalledWith('mercator');
      expect(instance.setProjection.mock.invocationCallOrder.at(-1)).toBeLessThan(
        instance.restoreCamera.mock.invocationCallOrder[0]!,
      );
    },
  );

  it('queues a reverse-projection restore while the engine is synchronising a newer projection', () => {
    const instance = fakeEngine();
    const factory = () => instance;
    let handle: GlobeEngineHandle;
    let changeMode: (mode: ViewMode) => void;
    const command: Command = (engine) => {
      handle = engine;
    };
    function StatefulHarness() {
      const [mode, setMode] = useState<ViewMode>('globe');
      useLayoutEffect(() => {
        changeMode = setMode;
      }, []);
      return <Harness factory={factory} command={command} mode={mode} />;
    }
    render(<StatefulHarness />);
    instance.setProjection.mockImplementationOnce(() => {
      handle.restoreCamera?.(lastCamera, 'globe');
      changeMode('globe');
    });
    act(() => changeMode('map'));
    expect(instance.setProjection).toHaveBeenLastCalledWith('globe');
    expect(instance.restoreCamera).toHaveBeenCalledExactlyOnceWith(lastCamera);
    expect(instance.setProjection.mock.invocationCallOrder.at(-1)).toBeLessThan(
      instance.restoreCamera.mock.invocationCallOrder[0]!,
    );
  });

  it.each(['focus', 'unqualified camera'] as const)(
    'defers a re-entrant %s until projection synchronisation returns',
    (kind) => {
      const instance = fakeEngine();
      const factory = () => instance;
      const order: string[] = [];
      let handle: GlobeEngineHandle;
      const command: Command = (engine) => {
        handle = engine;
      };
      const navigated = () => {
        order.push('navigation');
      };
      instance.flyTo.mockImplementation(navigated);
      instance.restoreCamera.mockImplementation(navigated);
      const view = render(<Harness factory={factory} command={command} />);
      instance.setProjection.mockImplementationOnce(() => {
        order.push('projection start');
        if (kind === 'focus') handle.flyTo(focus);
        else handle.restoreCamera?.(lastCamera);
        order.push('projection end');
      });
      view.rerender(<Harness factory={factory} command={command} mode="map" />);
      expect(order).toEqual(['projection start', 'projection end', 'navigation']);
      if (kind === 'focus') expect(instance.flyTo).toHaveBeenCalledExactlyOnceWith(focus);
      else expect(instance.restoreCamera).toHaveBeenCalledExactlyOnceWith(lastCamera);
    },
  );
});
