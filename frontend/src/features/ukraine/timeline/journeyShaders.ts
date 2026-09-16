/**
 * GLSL for the timeline journey. three.js prepends the common attributes and matrices, so
 * only the custom attributes and uniforms are declared here. Everything is hand-written and
 * compiled by the driver; nothing is fetched or evaluated, which keeps the Caddy CSP intact.
 */

/** The corridor floor: a faint world grid plus a transverse glow standing in for the front line. */
export const GROUND_VERTEX = /* glsl */ `
varying vec2 vWorld;
void main() {
  vec4 world = modelMatrix * vec4(position, 1.0);
  vWorld = world.xz;
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

export const GROUND_FRAGMENT = /* glsl */ `
precision mediump float;
uniform vec3 uGrid;
uniform vec3 uFront;
uniform float uFrontZ;
uniform float uCameraZ;
uniform float uTime;
varying vec2 vWorld;

float rule(float coord, float spacing, float width) {
  float edge = abs(fract(coord / spacing - 0.5) - 0.5) * spacing;
  return 1.0 - smoothstep(0.0, width, edge);
}

void main() {
  float grid = max(rule(vWorld.x, 7.0, 0.085), rule(vWorld.y, 7.0, 0.085));
  float away = abs(vWorld.y - uCameraZ);
  float fade = exp(-away * 0.012) * smoothstep(1.0, 14.0, away);
  float front = exp(-abs(vWorld.y - uFrontZ) * 0.42);
  float ripple = 0.72 + 0.28 * sin(vWorld.x * 0.28 + uTime * 0.9);
  vec3 colour = uGrid * grid * 0.75 + uFront * front * ripple * 1.5;
  float alpha = clamp(grid * 0.45 + front * 0.85, 0.0, 1.0) * fade;
  if (alpha < 0.004) discard;
  gl_FragColor = vec4(colour, alpha);
}
`;

/** The road itself: a tube coloured by phase that brightens around the reader's position. */
export const RIBBON_VERTEX = /* glsl */ `
attribute vec3 aColour;
varying vec3 vColour;
varying vec2 vRun;
void main() {
  vColour = aColour;
  vRun = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

export const RIBBON_FRAGMENT = /* glsl */ `
precision mediump float;
uniform float uProgress;
uniform float uTime;
varying vec3 vColour;
varying vec2 vRun;

void main() {
  float near = exp(-abs(vRun.x - uProgress) * 7.0);
  float pulse = 0.5 + 0.5 * sin(vRun.x * 46.0 - uTime * 1.6);
  float rim = pow(abs(vRun.y - 0.5) * 2.0, 2.0);
  float alpha = clamp(0.2 + near * 0.68 + pulse * 0.07, 0.0, 1.0) * (0.4 + rim * 0.6);
  gl_FragColor = vec4(vColour * (0.5 + near * 0.95), alpha);
}
`;

/** One upright marker per event, brightest at the event the reader is standing in front of. */
export const MARKER_VERTEX = /* glsl */ `
attribute vec3 aColour;
attribute float aIndex;
uniform float uActive;
varying vec3 vColour;
varying float vFocus;
varying vec2 vFace;
void main() {
  float focus = 1.0 - smoothstep(0.0, 1.8, abs(aIndex - uActive));
  vColour = aColour;
  vFocus = focus;
  vFace = uv;
  vec3 shaped = vec3(position.x * (0.65 + focus * 0.75), position.y * (0.75 + focus * 0.5), position.z);
  gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(shaped, 1.0);
}
`;

export const MARKER_FRAGMENT = /* glsl */ `
precision mediump float;
varying vec3 vColour;
varying float vFocus;
varying vec2 vFace;

void main() {
  float across = 1.0 - smoothstep(0.0, 0.5, abs(vFace.x - 0.5));
  float up = pow(1.0 - vFace.y, 1.7);
  float alpha = across * up * (0.16 + vFocus * 0.72);
  if (alpha < 0.004) discard;
  gl_FragColor = vec4(vColour * (0.55 + vFocus * 0.95), alpha);
}
`;

/** Drifting dust, tied to how far the reader has travelled so the field parallaxes past them. */
export const DUST_VERTEX = /* glsl */ `
attribute float aSeed;
uniform float uTime;
uniform float uTravel;
uniform float uSpan;
uniform float uSize;
uniform float uPixelRatio;
varying float vFade;
void main() {
  vec3 placed = position;
  float shift = uTravel * (0.55 + aSeed * 0.55) + uTime * (0.4 + aSeed * 0.9);
  placed.z = mod(placed.z + shift + uSpan * 0.5, uSpan) - uSpan * 0.5;
  placed.y += sin(uTime * 0.5 + aSeed * 8.0) * 0.45;
  vec4 view = modelViewMatrix * vec4(placed, 1.0);
  float depth = max(-view.z, 0.8);
  vFade = smoothstep(uSpan * 0.5, uSpan * 0.06, depth) * (0.25 + aSeed * 0.7);
  gl_Position = projectionMatrix * view;
  gl_PointSize = uSize * uPixelRatio * (14.0 / depth);
}
`;

export const DUST_FRAGMENT = /* glsl */ `
precision mediump float;
uniform vec3 uColour;
varying float vFade;
void main() {
  vec2 offset = gl_PointCoord - 0.5;
  float radius = dot(offset, offset);
  if (radius > 0.25) discard;
  gl_FragColor = vec4(uColour, vFade * (1.0 - smoothstep(0.0, 0.25, radius)));
}
`;
