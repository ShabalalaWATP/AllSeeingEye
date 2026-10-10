// Original deterministic pixels, shared within each realm without importing OGL.
import { generateNoiseTexture } from './evilEyeShader';

let sharedNoise: Uint8Array | undefined;
export function eyeNoise(): Uint8Array {
  return (sharedNoise ??= generateNoiseTexture(256));
}
