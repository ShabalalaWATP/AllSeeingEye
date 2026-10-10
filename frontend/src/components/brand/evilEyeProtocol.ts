/** Internal, same-origin worker messages. No application or account data crosses this boundary. */
export interface EyeOptions {
  eyeColor: string;
  intensity: number;
  pupilSize: number;
  irisWidth: number;
  glowIntensity: number;
  scale: number;
  noiseScale: number;
  pupilFollow: number;
  flameSpeed: number;
  backgroundColor: string;
  lightMode: boolean;
  transparent: boolean;
}

export interface EyeSize {
  width: number;
  height: number;
}

export interface EyeFrame {
  /** The document requestAnimationFrame timestamp, never a worker-relative clock. */
  time: number;
  mouse: [number, number];
}

export interface EyeSurface {
  resize(size: EyeSize): void;
  /** False means the worker has not started or already has one frame in flight. */
  render(frame: EyeFrame): boolean;
  dispose(): void;
}

export type EyeRequest =
  | { type: 'init'; canvas: OffscreenCanvas; options: EyeOptions; size: EyeSize; noise: Uint8Array }
  | { type: 'resize'; size: EyeSize }
  | { type: 'frame'; frame: EyeFrame }
  | { type: 'dispose' };

export type EyeReply =
  | { type: 'ready' | 'frame' | 'resized' | 'disposed' }
  | { type: 'failed'; phase: 'startup' | 'render' | 'lost' };
