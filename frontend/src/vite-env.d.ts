/// <reference types="vite/client" />

/** Approval verified against the exact policy content by the local build tooling. */
declare module 'virtual:policy-approval' {
  const approved: boolean;
  export default approved;
}

/** The hashed MapLibre worker chunk in a build; empty in development and tests. */
declare module 'virtual:maplibre-worker-url' {
  const url: string;
  export default url;
}
