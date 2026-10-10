// Match route definitions rather than URLs, including decoded and mixed-case paths.
const PUBLIC_DOCUMENT_PATHS = new Set([
  '/enterprise',
  '/privacy',
  '/privacy/requests',
  '/attributions',
]);

interface SessionRouter {
  state: { matches: { route: { path?: string } }[] };
  subscribe: (listener: () => void) => () => void;
}

const loadBootstrap = async () => (await import('@/stores/auth')).useAuthStore.getState().bootstrap;

/** Public documents never load account code or refresh a saved session cookie. */
export function watchSessionRoute(
  router: SessionRouter,
  reportFailure: (failed: boolean) => void,
  load = loadBootstrap,
): () => void {
  let live = true;
  let started = false;
  let loading = false;
  const isPublic = () =>
    router.state.matches.some(({ route }) => PUBLIC_DOCUMENT_PATHS.has(route.path ?? ''));
  const visit = () => {
    if (isPublic()) {
      reportFailure(false);
      return;
    }
    if (started || loading) return;
    loading = true;
    void load()
      .then((bootstrap) => {
        loading = false;
        // Import completion may follow a return to a public page or an unmount.
        if (!live || isPublic()) return;
        started = true;
        return bootstrap().then(() => {
          if (live) reportFailure(false);
        });
      })
      .catch(() => {
        loading = false;
        started = false;
        if (live && !isPublic()) reportFailure(true);
      });
  };
  visit();
  const unsubscribe = router.subscribe(visit);
  return () => {
    live = false;
    unsubscribe();
  };
}
