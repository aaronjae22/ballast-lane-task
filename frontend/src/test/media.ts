/**
 * The test setup's matchMedia matches nothing, which is a narrow screen. This makes the `sm`
 * breakpoint (48em) match, as on a desktop, defined the same way setup.ts defines it. It
 * returns the function that puts the narrow screen back.
 */
export function onWideScreen(): () => void {
  const narrow: unknown = Reflect.get(window, 'matchMedia')
  const define = (value: unknown) => {
    Object.defineProperty(window, 'matchMedia', { writable: true, value })
  }
  define((query: string) => ({
    matches: query.includes('48em'),
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }))
  return () => {
    define(narrow)
  }
}
