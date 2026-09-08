import { act, render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.unmock('./EvilEye');
const graphics = vi.hoisted(() => ({
  initialiseFails: false,
  render: vi.fn(),
  release: vi.fn(),
  frames: new Map<number, FrameRequestCallback>(),
  next: 0,
}));
vi.mock('./evilEyeShader', () => ({
  generateNoiseTexture: () => new Uint8Array(4),
  hexToVec3: () => [0, 0, 0],
  vertexShader: '',
  fragmentShader: '',
}));
vi.mock('ogl', () => ({
  Renderer: class {
    gl = {
      canvas: document.createElement('canvas'),
      clearColor: vi.fn(),
      deleteTexture: graphics.release,
      getExtension: () => ({ loseContext: graphics.release }),
    };
    constructor() {
      if (graphics.initialiseFails) throw new Error('No graphics context');
    }
    setSize = vi.fn();
    render = graphics.render;
  },
  Texture: class {
    texture = {};
  },
  Triangle: class {
    remove = graphics.release;
  },
  Program: class {
    uniforms: Record<string, { value: unknown }>;
    constructor(_gl: unknown, props: { uniforms: Record<string, { value: unknown }> }) {
      this.uniforms = props.uniforms;
    }
    remove = graphics.release;
  },
  Mesh: class {
    scene = null;
  },
}));
import EvilEye from './EvilEye';

beforeEach(() => {
  graphics.initialiseFails = false;
  graphics.render.mockReset();
  graphics.release.mockReset();
  graphics.frames.clear();
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    const id = ++graphics.next;
    graphics.frames.set(id, callback);
    return id;
  });
  vi.stubGlobal('cancelAnimationFrame', (id: number) => graphics.frames.delete(id));
});

function frame() {
  const entry = [...graphics.frames.entries()][0];
  if (!entry) throw new Error('Expected a scheduled animation frame');
  const [id, callback] = entry;
  graphics.frames.delete(id);
  act(() => {
    callback(1000);
  });
}

describe('Evil Eye graphics lifetime', () => {
  it('keeps the original captured eye if graphics initialisation fails', () => {
    graphics.initialiseFails = true;
    const { container } = render(<EvilEye />);
    expect(container.querySelector('img')).toHaveAttribute('src', '/brand/eye-512.png');
    expect(container.querySelector('canvas')).toBeNull();
    expect(graphics.frames.size).toBe(0);
  });

  it('stops and releases graphics on context loss without a recovery loop', () => {
    const { container, rerender } = render(<EvilEye />);
    frame();
    const canvas = container.querySelector('canvas')!;
    const lost = new Event('webglcontextlost', { cancelable: true });
    act(() => {
      canvas.dispatchEvent(lost);
    });
    expect(lost.defaultPrevented).toBe(true);
    expect(container.querySelector('canvas')).toBeNull();
    expect(container.querySelector('img')).toBeVisible();
    expect(graphics.release).toHaveBeenCalled();
    expect(graphics.frames.size).toBe(0);
    rerender(<EvilEye paused />);
    rerender(<EvilEye paused={false} />);
    expect(graphics.frames.size).toBe(0);
  });

  it('contains rendering failure and cancels the next frame', () => {
    graphics.render.mockImplementation(() => {
      throw new Error('GPU reset');
    });
    const { container } = render(<EvilEye />);
    frame();
    expect(container.querySelector('canvas')).toBeNull();
    expect(graphics.frames.size).toBe(0);
  });

  it('releases the frame, canvas and graphics resources on unmount', () => {
    const { unmount } = render(<EvilEye />);
    expect(graphics.frames.size).toBe(1);
    unmount();
    expect(graphics.frames.size).toBe(0);
    expect(graphics.release).toHaveBeenCalledTimes(4);
  });
});
