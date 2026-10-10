/** Public titles do not depend on the signed-in navigation directory. */
export const APP_TITLE = 'The All Seeing Eye';
export const NOT_FOUND_TITLE = 'Page not found';

/** Add the application name once, including for pages with their own explicit title. */
export function withAppTitle(title: string): string {
  return title === APP_TITLE ? APP_TITLE : `${title} · ${APP_TITLE}`;
}
