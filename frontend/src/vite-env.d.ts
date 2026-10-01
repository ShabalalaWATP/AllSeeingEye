/// <reference types="vite/client" />

/** The hashed MapLibre worker chunk in a build; empty in development and tests. */
declare module 'virtual:maplibre-worker-url' {
  const url: string;
  export default url;
}
