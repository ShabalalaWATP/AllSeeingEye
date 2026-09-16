/**
 * The WebGL layer of the timeline journey: a corridor of light through the war, with a phase
 * coloured road, an upright marker at every event, drifting dust and a transverse glow standing
 * in for the front line. Loaded lazily in its own chunk and driven entirely by the React shell,
 * which owns the reading experience; nothing here is needed to read the timeline.
 */
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  CatmullRomCurve3,
  Color,
  DoubleSide,
  FogExp2,
  InstancedBufferAttribute,
  InstancedMesh,
  Mesh,
  Object3D,
  PerspectiveCamera,
  PlaneGeometry,
  Points,
  Scene,
  ShaderMaterial,
  TubeGeometry,
  Vector3,
  WebGLRenderer,
} from 'three';

import {
  DUST_FRAGMENT,
  DUST_VERTEX,
  GROUND_FRAGMENT,
  GROUND_VERTEX,
  MARKER_FRAGMENT,
  MARKER_VERTEX,
  RIBBON_FRAGMENT,
  RIBBON_VERTEX,
} from './journeyShaders';
import {
  PATH_MARGIN,
  STOP_SPACING,
  approach,
  pathLength,
  pathPoint,
  stopProgress,
} from './journey';

export interface JourneySceneOptions {
  canvas: HTMLCanvasElement;
  /** One CSS colour per stop, in travel order. */
  colours: string[];
  background: string;
  width: number;
  height: number;
}

export interface JourneyScene {
  /** Travel target as a stop index; the camera eases towards it. */
  travelTo(index: number): void;
  setPlaying(playing: boolean): void;
  setRunning(running: boolean): void;
  resize(width: number, height: number): void;
  dispose(): void;
}

const GROUND_Y = -2.6;
const EYE_HEIGHT = 2.5;
const LEAD_UNITS = 7;
const MAX_DELTA = 0.05;

function dustField(count: number, span: number, spread: number): BufferGeometry {
  const positions = new Float32Array(count * 3);
  const seeds = new Float32Array(count);
  for (let i = 0; i < count; i += 1) {
    // A deterministic scatter: no randomness to reproduce between reloads.
    const golden = (i * 0.61803398875) % 1;
    const ring = (i * 0.7548776662) % 1;
    positions[i * 3] = (golden - 0.5) * spread;
    positions[i * 3 + 1] = GROUND_Y + 0.4 + ring * 14;
    positions[i * 3 + 2] = (i / count - 0.5) * span;
    seeds[i] = ring;
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(positions, 3));
  geometry.setAttribute('aSeed', new BufferAttribute(seeds, 1));
  return geometry;
}

/** Colour of the road at a point along it, blended across the boundary between two phases. */
function blendAt(run: number, length: number, palette: Color[], out: Color): Color {
  const slot = (run * length - PATH_MARGIN) / STOP_SPACING;
  const low = Math.min(palette.length - 1, Math.max(0, Math.floor(slot)));
  const high = Math.min(palette.length - 1, low + 1);
  const raw = Math.min(1, Math.max(0, slot - low));
  return out
    .copy(palette[low] ?? palette[0] ?? new Color())
    .lerp(palette[high] ?? palette[low] ?? new Color(), raw * raw * (3 - 2 * raw));
}

export function createJourneyScene(options: JourneySceneOptions): JourneyScene {
  const count = Math.max(options.colours.length, 1);
  const length = pathLength(count);
  const palette = options.colours.map((colour) => new Color(colour));
  if (palette.length === 0) palette.push(new Color('#9fb4c7'));
  const ground = new Color(options.background);

  const renderer = new WebGLRenderer({ canvas: options.canvas, antialias: options.width > 900 });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(options.width, options.height, false);
  renderer.setClearColor(ground, 1);

  const scene = new Scene();
  scene.fog = new FogExp2(ground.getHex(), 0.02);
  const camera = new PerspectiveCamera(58, options.width / Math.max(options.height, 1), 0.1, 420);

  const sample = (at: number, out: Vector3): Vector3 => {
    const [x, y, z] = pathPoint(at, length);
    return out.set(x, y, z);
  };
  const curve = new CatmullRomCurve3(
    Array.from({ length: 80 }, (_, i) => sample(i / 79, new Vector3())),
  );

  const ribbonGeometry = new TubeGeometry(curve, Math.min(count * 10 + 40, 420), 0.42, 6, false);
  const uv = ribbonGeometry.getAttribute('uv');
  const colours = new Float32Array(uv.count * 3);
  const scratch = new Color();
  for (let i = 0; i < uv.count; i += 1) {
    blendAt(uv.getX(i), length, palette, scratch);
    colours[i * 3] = scratch.r;
    colours[i * 3 + 1] = scratch.g;
    colours[i * 3 + 2] = scratch.b;
  }
  ribbonGeometry.setAttribute('aColour', new BufferAttribute(colours, 3));
  const ribbonUniforms = { uProgress: { value: 0 }, uTime: { value: 0 } };
  const ribbonMaterial = new ShaderMaterial({
    vertexShader: RIBBON_VERTEX,
    fragmentShader: RIBBON_FRAGMENT,
    uniforms: ribbonUniforms,
    transparent: true,
    depthWrite: false,
    side: DoubleSide,
    blending: AdditiveBlending,
  });
  scene.add(new Mesh(ribbonGeometry, ribbonMaterial));

  const groundGeometry = new PlaneGeometry(320, 560, 1, 1);
  groundGeometry.rotateX(-Math.PI / 2);
  const groundUniforms = {
    uGrid: { value: new Color('#3a4358') },
    uFront: { value: palette[0]?.clone() ?? new Color('#ff5a3c') },
    uFrontZ: { value: 0 },
    uCameraZ: { value: 0 },
    uTime: { value: 0 },
  };
  const groundMaterial = new ShaderMaterial({
    vertexShader: GROUND_VERTEX,
    fragmentShader: GROUND_FRAGMENT,
    uniforms: groundUniforms,
    transparent: true,
    depthWrite: false,
  });
  const groundMesh = new Mesh(groundGeometry, groundMaterial);
  groundMesh.position.y = GROUND_Y;
  scene.add(groundMesh);

  const markerGeometry = new PlaneGeometry(1.5, 9, 1, 1);
  markerGeometry.translate(0, 4.5, 0);
  const markerUniforms = { uActive: { value: 0 } };
  const markerMaterial = new ShaderMaterial({
    vertexShader: MARKER_VERTEX,
    fragmentShader: MARKER_FRAGMENT,
    uniforms: markerUniforms,
    transparent: true,
    depthWrite: false,
    side: DoubleSide,
    blending: AdditiveBlending,
  });
  const markers = new InstancedMesh(markerGeometry, markerMaterial, count);
  const markerColours = new Float32Array(count * 3);
  const markerIndices = new Float32Array(count);
  const dummy = new Object3D();
  const here = new Vector3();
  const ahead = new Vector3();
  for (let i = 0; i < count; i += 1) {
    const at = stopProgress(i, count);
    sample(at, here);
    sample(Math.min(1, at + 0.004), ahead);
    const yaw = Math.atan2(here.x - ahead.x, here.z - ahead.z);
    dummy.position.set(here.x + (i % 2 === 0 ? 3.1 : -3.1), GROUND_Y, here.z);
    dummy.rotation.set(0, yaw, 0);
    dummy.updateMatrix();
    markers.setMatrixAt(i, dummy.matrix);
    const colour = palette[i] ?? palette[palette.length - 1] ?? new Color();
    markerColours[i * 3] = colour.r;
    markerColours[i * 3 + 1] = colour.g;
    markerColours[i * 3 + 2] = colour.b;
    markerIndices[i] = i;
  }
  markers.geometry.setAttribute('aColour', new InstancedBufferAttribute(markerColours, 3));
  markers.geometry.setAttribute('aIndex', new InstancedBufferAttribute(markerIndices, 1));
  markers.instanceMatrix.needsUpdate = true;
  markers.frustumCulled = false;
  scene.add(markers);

  const dustCount = Math.round(Math.min(1700, Math.max(420, options.width * 1.1)));
  const dustSpan = 260;
  const dustGeometry = dustField(dustCount, dustSpan, 120);
  const dustUniforms = {
    uTime: { value: 0 },
    uTravel: { value: 0 },
    uSpan: { value: dustSpan },
    uSize: { value: 2.4 },
    uPixelRatio: { value: renderer.getPixelRatio() },
    uColour: { value: palette[0]?.clone() ?? new Color('#ffffff') },
  };
  const dustMaterial = new ShaderMaterial({
    vertexShader: DUST_VERTEX,
    fragmentShader: DUST_FRAGMENT,
    uniforms: dustUniforms,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
  });
  const dust = new Points(dustGeometry, dustMaterial);
  dust.frustumCulled = false;
  scene.add(dust);

  let target = stopProgress(0, count);
  let travel = target;
  let activeTarget = 0;
  let active = 0;
  let playing = true;
  let running = false;
  let frame = 0;
  let last = 0;
  let clock = 0;
  const eye = new Vector3();
  const focus = new Vector3();
  const tint = new Color();
  const white = new Color('#ffffff');

  const draw = (delta: number): void => {
    travel = approach(travel, target, delta);
    active = approach(active, activeTarget, delta, 5);
    if (playing) clock += delta;
    const lead = LEAD_UNITS / length;
    sample(travel - lead, eye);
    eye.y += EYE_HEIGHT;
    camera.position.copy(eye);
    sample(Math.min(1, travel + lead * 2.2), focus);
    focus.y += EYE_HEIGHT * 0.6;
    camera.lookAt(focus);
    dust.position.set(camera.position.x, 0, camera.position.z);
    groundMesh.position.set(camera.position.x, GROUND_Y, camera.position.z - 180);
    blendAt(travel, length, palette, tint);
    ribbonUniforms.uProgress.value = travel;
    ribbonUniforms.uTime.value = clock;
    markerUniforms.uActive.value = active;
    groundUniforms.uTime.value = clock;
    groundUniforms.uCameraZ.value = camera.position.z;
    // Decorative: the glow slides towards and away from the reader as the journey advances.
    groundUniforms.uFrontZ.value = camera.position.z - 46 - Math.sin(travel * Math.PI * 3.1) * 34;
    groundUniforms.uFront.value.copy(tint);
    dustUniforms.uTime.value = clock;
    dustUniforms.uTravel.value = -camera.position.z;
    dustUniforms.uColour.value.copy(tint).lerp(white, 0.35);
    renderer.render(scene, camera);
  };

  const settled = (): boolean => travel === target && active === activeTarget;

  const tick = (now: number): void => {
    if (!running) return;
    const delta = last === 0 ? 1 / 60 : Math.min((now - last) / 1000, MAX_DELTA);
    last = now;
    draw(delta);
    // A still, paused journey costs nothing: stop asking for frames until something moves.
    if (!playing && settled()) {
      frame = 0;
      return;
    }
    frame = window.requestAnimationFrame(tick);
  };

  const wake = (): void => {
    if (!running || frame !== 0) return;
    last = 0;
    frame = window.requestAnimationFrame(tick);
  };

  draw(0);

  return {
    travelTo(index: number): void {
      activeTarget = Math.min(count - 1, Math.max(0, index));
      target = stopProgress(activeTarget, count);
      wake();
    },
    setPlaying(next: boolean): void {
      playing = next;
      wake();
    },
    setRunning(next: boolean): void {
      if (running === next) return;
      running = next;
      if (next) {
        last = 0;
        wake();
      } else if (frame !== 0) {
        window.cancelAnimationFrame(frame);
        frame = 0;
      }
    },
    resize(width: number, height: number): void {
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(width, height, false);
      dustUniforms.uPixelRatio.value = renderer.getPixelRatio();
      camera.aspect = width / Math.max(height, 1);
      camera.updateProjectionMatrix();
      if (frame === 0) draw(0);
    },
    dispose(): void {
      if (frame !== 0) window.cancelAnimationFrame(frame);
      frame = 0;
      running = false;
      for (const geometry of [ribbonGeometry, groundGeometry, markerGeometry, dustGeometry]) {
        geometry.dispose();
      }
      for (const material of [ribbonMaterial, groundMaterial, markerMaterial, dustMaterial]) {
        material.dispose();
      }
      markers.dispose();
      scene.clear();
      renderer.dispose();
      renderer.forceContextLoss();
    },
  };
}
