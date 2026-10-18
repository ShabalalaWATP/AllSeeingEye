/** Operator identity for the shared footer, read at build time from the hashed policy content. */
declare module 'virtual:policy-footer' {
  const details: { operator: string | null; contact: string | null; address: string | null };
  export default details;
}
