import type { Layer } from '@deck.gl/core';

// IconLayer/TextLayer flip the SVG quad's Y axis, so its front face is clockwise.
// Keep this explicit for tangent AND billboard symbols: GlobeView still culls
// back faces when it changes to WebMercatorViewport above zoom 12. MapView has
// no face culling, so the same winding is harmless there.
// The numeric GL_FRONT_FACE key avoids luma sending a string to gl.frontFace.
export const SYMBOL_WINDING: NonNullable<Layer['props']['parameters']> & Record<number, number> = {
  2886: 2304, // GL_FRONT_FACE: GL_CW
};
