import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { EyeOptions } from './evilEyeProtocol';

const gl = vi.hoisted(() => ({
  canvas: new EventTarget() as EventTarget & { width: number; height: number },
  clearColor: vi.fn(),
  deleteTexture: vi.fn(),
  lose: vi.fn(),
  LINEAR: 9729,
  REPEAT: 10497,
}));
const graphics = vi.hoisted(() => {
  const uniforms: Record<string, { value: unknown }> = {};
  return {
    renderer: vi.fn(),
    texture: vi.fn(),
    program: vi.fn(),
    geometry: vi.fn(),
    render: vi.fn(),
    removeProgram: vi.fn(),
    removeGeometry: vi.fn(),
    uniforms,
  };
});
vi.mock('ogl', () => ({
  Renderer: class {
    gl = { ...gl, getExtension: () => ({ loseContext: gl.lose }) };
    constructor(options: unknown) {
      graphics.renderer(options);
    }
    setSize(width: number, height: number) {
      gl.canvas.width = width;
      gl.canvas.height = height;
    }
    render = graphics.render;
  },
  Texture: class {
    texture = {};
    constructor(context: unknown, options: unknown) {
      graphics.texture(context, options, this);
    }
  },
  Program: class {
    uniforms: Record<string, { value: unknown }>;
    constructor(context: unknown, options: { uniforms: Record<string, { value: unknown }> }) {
      graphics.program(context, options);
      this.uniforms = options.uniforms;
      graphics.uniforms = this.uniforms;
    }
    remove = graphics.removeProgram;
  },
  Triangle: class {
    constructor() {
      graphics.geometry();
    }
    remove = graphics.removeGeometry;
  },
  Mesh: class {
    scene = null;
  },
}));
import { createEyeRenderer, eyeNoise } from './evilEyeRenderer';
import { fragmentShader, vertexShader } from './evilEyeShader';

const options: EyeOptions = {
  eyeColor: '#FF6F37',
  intensity: 1.5,
  pupilSize: 0.6,
  irisWidth: 0.25,
  glowIntensity: 0.35,
  scale: 0.8,
  noiseScale: 1,
  pupilFollow: 1,
  flameSpeed: 1,
  backgroundColor: '#000000',
  lightMode: false,
  transparent: true,
};
beforeEach(() => {
  for (const mock of [
    graphics.renderer,
    graphics.texture,
    graphics.program,
    graphics.geometry,
    graphics.render,
    graphics.removeProgram,
    graphics.removeGeometry,
    gl.deleteTexture,
    gl.lose,
  ])
    mock.mockReset();
});
function create(onLost = vi.fn()) {
  return createEyeRenderer(
    gl.canvas as unknown as OffscreenCanvas,
    options,
    { width: 200, height: 100 },
    onLost,
  );
}

describe('shared original eye renderer', () => {
  it('retains context attributes, exact shaders, texture filtering and uniform values', () => {
    const renderer = create();
    expect(graphics.renderer).toHaveBeenCalledWith({
      canvas: gl.canvas,
      alpha: true,
      premultipliedAlpha: false,
      dpr: 1,
    });
    expect(graphics.program.mock.calls[0]?.[1]).toMatchObject({
      vertex: vertexShader,
      fragment: fragmentShader,
    });
    expect(graphics.texture.mock.calls[0]?.[1]).toEqual({
      image: eyeNoise(),
      width: 256,
      height: 256,
      generateMipmaps: false,
      flipY: false,
    });
    expect(graphics.texture.mock.calls[0]?.[2]).toMatchObject({
      minFilter: gl.LINEAR,
      magFilter: gl.LINEAR,
      wrapS: gl.REPEAT,
      wrapT: gl.REPEAT,
    });
    expect(
      Object.fromEntries(
        Object.entries(graphics.uniforms)
          .filter(([key]) => key !== 'uNoiseTexture')
          .map(([key, value]) => [key, value.value]),
      ),
    ).toEqual({
      uTime: 0,
      uResolution: [200, 100, 2],
      uPupilSize: 0.6,
      uIrisWidth: 0.25,
      uGlowIntensity: 0.35,
      uIntensity: 1.5,
      uScale: 0.8,
      uNoiseScale: 1,
      uMouse: [0, 0],
      uPupilFollow: 1,
      uFlameSpeed: 1,
      uEyeColor: [1, 111 / 255, 55 / 255],
      uBgColor: [0, 0, 0],
      uLightMode: false,
      uTransparent: true,
    });
    renderer.resize({ width: 300, height: 120 });
    expect(graphics.uniforms.uResolution?.value).toEqual([300, 120, 2.5]);
    renderer.render({ time: 123456, mouse: [0.2, -0.3] });
    expect(graphics.uniforms.uTime?.value).toBe(123.456);
    expect(graphics.uniforms.uMouse?.value).toEqual([0.2, -0.3]);
    expect(graphics.render).toHaveBeenCalledOnce();
    renderer.dispose();
  });

  it('releases each resource once and removes context-loss callbacks before intentional disposal', () => {
    const lost = vi.fn();
    const renderer = create(lost);
    const event = new Event('webglcontextlost', { cancelable: true });
    gl.canvas.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    expect(lost).toHaveBeenCalledOnce();
    renderer.dispose();
    renderer.dispose();
    gl.canvas.dispatchEvent(new Event('webglcontextlost'));
    expect(lost).toHaveBeenCalledOnce();
    for (const release of [
      graphics.removeProgram,
      graphics.removeGeometry,
      gl.deleteTexture,
      gl.lose,
    ])
      expect(release).toHaveBeenCalledOnce();
  });

  it.each(['texture', 'geometry', 'program'] as const)(
    'releases partially constructed resources after %s failure',
    (stage) => {
      graphics[stage].mockImplementation(() => {
        throw new Error('Graphics unavailable');
      });
      expect(() => create()).toThrow('Graphics unavailable');
      expect(gl.lose).toHaveBeenCalledOnce();
      expect(gl.deleteTexture).toHaveBeenCalledTimes(stage === 'texture' ? 0 : 1);
      expect(graphics.removeGeometry).toHaveBeenCalledTimes(stage === 'program' ? 1 : 0);
      expect(graphics.removeProgram).not.toHaveBeenCalled();
    },
  );

  it('continues releasing remaining resources when a lost context rejects one cleanup', () => {
    const renderer = create();
    graphics.removeProgram.mockImplementation(() => {
      throw new Error('Already lost');
    });
    renderer.dispose();
    expect(gl.lose).toHaveBeenCalledOnce();
    expect(gl.deleteTexture).toHaveBeenCalledOnce();
    expect(graphics.removeGeometry).toHaveBeenCalledOnce();
  });
});
