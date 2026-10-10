// Original React Bits rendering, shared by the DOM and worker surfaces.
// Licence/provenance: EvilEye.tsx and THIRD_PARTY_NOTICES.md.
import { Renderer, Program, Mesh, Triangle, Texture } from 'ogl';

import type { EyeFrame, EyeOptions, EyeSize } from './evilEyeProtocol';
import { generateNoiseTexture, hexToVec3, vertexShader, fragmentShader } from './evilEyeShader';

// Only immutable CPU pixels are shared. Each surface owns and releases its GPU texture.
let sharedNoise: Uint8Array | undefined;
export function eyeNoise(): Uint8Array {
  return (sharedNoise ??= generateNoiseTexture(256));
}

export function createEyeRenderer(
  canvas: HTMLCanvasElement | OffscreenCanvas,
  options: EyeOptions,
  size: EyeSize,
  onLost: () => void,
  noise = eyeNoise(),
) {
  const disposers: (() => void)[] = [];
  let disposed = false;
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    for (const release of disposers.reverse()) {
      try {
        release();
      } catch {
        // Context loss can already have released a resource.
      }
    }
  };
  try {
    // OGL 1.0.11 accepts a supplied OffscreenCanvas and guards access to .style.
    // Its declaration only names HTMLCanvasElement; keep that adapter at this boundary.
    const renderer = new Renderer({
      canvas: canvas as HTMLCanvasElement,
      alpha: true,
      premultipliedAlpha: false,
      dpr: 1,
    });
    const gl = renderer.gl;
    disposers.push(() => gl.getExtension('WEBGL_lose_context')?.loseContext());
    const lost = (event: Event) => {
      event.preventDefault();
      if (!disposed) onLost();
    };
    canvas.addEventListener('webglcontextlost', lost);
    disposers.push(() => canvas.removeEventListener('webglcontextlost', lost));
    gl.clearColor(0, 0, 0, 0);
    const noiseTexture = new Texture(gl, {
      image: noise,
      width: 256,
      height: 256,
      generateMipmaps: false,
      flipY: false,
    });
    disposers.push(() => gl.deleteTexture(noiseTexture.texture));
    noiseTexture.minFilter = gl.LINEAR;
    noiseTexture.magFilter = gl.LINEAR;
    noiseTexture.wrapS = gl.REPEAT;
    noiseTexture.wrapT = gl.REPEAT;
    renderer.setSize(size.width, size.height);
    const resolution = () => [canvas.width, canvas.height, canvas.width / canvas.height];
    const geometry = new Triangle(gl);
    disposers.push(() => geometry.remove());
    const uniforms = {
      uTime: { value: 0 },
      uResolution: { value: resolution() },
      uNoiseTexture: { value: noiseTexture },
      uPupilSize: { value: options.pupilSize },
      uIrisWidth: { value: options.irisWidth },
      uGlowIntensity: { value: options.glowIntensity },
      uIntensity: { value: options.intensity },
      uScale: { value: options.scale },
      uNoiseScale: { value: options.noiseScale },
      uMouse: { value: [0, 0] },
      uPupilFollow: { value: options.pupilFollow },
      uFlameSpeed: { value: options.flameSpeed },
      uEyeColor: { value: hexToVec3(options.eyeColor) },
      uBgColor: { value: hexToVec3(options.backgroundColor) },
      uLightMode: { value: options.lightMode },
      uTransparent: { value: options.transparent },
    };
    const program = new Program(gl, { vertex: vertexShader, fragment: fragmentShader, uniforms });
    disposers.push(() => program.remove());
    const mesh = new Mesh(gl, { geometry, program });
    return {
      resize(next: EyeSize) {
        renderer.setSize(next.width, next.height);
        uniforms.uResolution.value = resolution();
      },
      render(frame: EyeFrame) {
        uniforms.uMouse.value = frame.mouse;
        uniforms.uTime.value = frame.time * 0.001;
        renderer.render({ scene: mesh });
      },
      dispose,
    };
  } catch (error) {
    dispose();
    throw error;
  }
}
