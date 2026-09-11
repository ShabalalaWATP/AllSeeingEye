import { act, fireEvent, render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.unmock('./EvilEye');
const graphics = vi.hoisted(() => ({
  initialiseFails: false,
  render: vi.fn(),
  release: vi.fn(),
  frames: new Map<number, FrameRequestCallback>(),
  uniforms: [] as Record<string, { value: unknown }>[],
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
      graphics.uniforms.push(this.uniforms);
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
  graphics.uniforms.length = 0;
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    const id = ++graphics.next;
    graphics.frames.set(id, callback);
    return id;
  });
  vi.stubGlobal('cancelAnimationFrame', (id: number) => graphics.frames.delete(id));
});

function frame(time = 1000) {
  const entry = [...graphics.frames.entries()][0];
  if (!entry) throw new Error('Expected a scheduled animation frame');
  const [id, callback] = entry;
  graphics.frames.delete(id);
  act(() => {
    callback(time);
  });
}

describe('Evil Eye graphics lifetime', () => {
  it('opts into transparency only when requested and hides the capture after rendering', () => {
    const { container, rerender } = render(<EvilEye />);
    expect(graphics.uniforms.at(-1)?.uTransparent?.value).toBe(false);
    expect(container.querySelector('img')).toBeVisible();
    frame();
    expect(container.querySelector('img')).not.toBeVisible();
    rerender(<EvilEye transparent />);
    expect(graphics.uniforms.at(-1)?.uTransparent?.value).toBe(true);
    expect(container.querySelector('img')).toBeVisible();
    frame();
    expect(container.querySelector('img')).not.toBeVisible();
    expect(container.querySelectorAll('canvas')).toHaveLength(1);
  });

  it('keeps the original captured eye if graphics initialisation fails', () => {
    graphics.initialiseFails = true;
    const { container } = render(<EvilEye />);
    expect(container.querySelector('img')).toHaveAttribute('src', '/brand/eye-512.png');
    expect(container.querySelector('canvas')).toBeNull();
    expect(graphics.frames.size).toBe(0);
  });

  it('stops and releases graphics on context loss without a recovery loop', () => {
    const { container, rerender } = render(<EvilEye transparent />);
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
    rerender(<EvilEye transparent paused />);
    rerender(<EvilEye transparent paused={false} />);
    expect(graphics.frames.size).toBe(0);
  });

  it('contains rendering failure and cancels the next frame', () => {
    graphics.render.mockImplementation(() => {
      throw new Error('GPU reset');
    });
    const { container } = render(<EvilEye />);
    frame();
    expect(container.querySelector('canvas')).toBeNull();
    expect(container.querySelector('img')).toBeVisible();
    expect(graphics.frames.size).toBe(0);
  });

  it('retains the capture when initially paused until a successful first frame', () => {
    const { container, rerender } = render(<EvilEye transparent paused />);
    expect(container.querySelector('img')).toBeVisible();
    expect(graphics.frames.size).toBe(0);
    rerender(<EvilEye transparent />);
    frame();
    expect(container.querySelector('img')).not.toBeVisible();
  });

  it('caps rendered frames and resumes without rebuilding a graphics context', () => {
    const { rerender } = render(<EvilEye transparent maxFps={24} />);
    frame(1000);
    frame(1016);
    frame(1032);
    frame(1048);
    expect(graphics.render).toHaveBeenCalledTimes(2);
    rerender(<EvilEye transparent maxFps={24} paused />);
    frame(1064);
    expect(graphics.frames.size).toBe(0);
    rerender(<EvilEye transparent maxFps={24} />);
    frame(1200);
    expect(graphics.render).toHaveBeenCalledTimes(3);
    expect(graphics.uniforms).toHaveLength(1);
  });

  it('moves the pupil towards the pointer using the original shader uniform', () => {
    const { container } = render(<EvilEye transparent pupilFollow={1} />);
    const surface = container.querySelector('canvas')!.parentElement!;
    vi.spyOn(surface, 'getBoundingClientRect').mockReturnValue({
      left: 0,
      top: 0,
      right: 136,
      bottom: 64,
      width: 136,
      height: 64,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });
    fireEvent.mouseMove(surface, { clientX: 136, clientY: 0 });
    frame();
    const uniforms = graphics.uniforms.at(-1)!;
    expect(uniforms.uPupilFollow?.value).toBe(1);
    expect(uniforms.uMouse?.value).toEqual([0.05, 0.05]);
    fireEvent.mouseLeave(surface);
    frame(1050);
    expect(uniforms.uMouse?.value).toEqual([0.0475, 0.0475]);
  });

  it('releases the frame, canvas and graphics resources on unmount', () => {
    const { unmount } = render(<EvilEye />);
    expect(graphics.frames.size).toBe(1);
    unmount();
    expect(graphics.frames.size).toBe(0);
    expect(graphics.release).toHaveBeenCalledTimes(4);
  });
});
