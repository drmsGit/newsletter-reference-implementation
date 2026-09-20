import createClient from 'openapi-fetch'

import type { paths } from './schema'

/**
 * The one HTTP client this application uses.
 *
 * `openapi-fetch` is a thin wrapper over the browser's own `fetch`. What it adds
 * is type safety against `schema.d.ts`, which is generated from the backend's
 * OpenAPI document: ask for a path that does not exist, or send a body of the
 * wrong shape, and the compiler refuses rather than the server. That is ADR-170
 * point 4 -- the contract cannot silently fork, because there is one description
 * of it and the client is derived from it.
 */

/**
 * **`baseUrl` is empty on purpose, and it is ADR-168 point 3 in one line.**
 *
 * An empty base URL makes every request relative, so the browser sends it to
 * whatever origin the page was served from. In production FastAPI serves this
 * app's build output, so that is the backend. In development Vite serves the
 * page and proxies the API paths (`vite.config.ts`), so it is still one origin
 * as far as the browser is concerned.
 *
 * Writing `http://localhost:8000` here instead would work and would be a
 * mistake: the page would become cross-origin, the session cookie would need
 * `samesite="none"` and the backend would need a CORS policy. Those are the two
 * controls ADR-168 exists to avoid having to get right.
 */
const client = createClient<paths>({
  baseUrl: '',
  /**
   * Look `fetch` up at call time rather than letting `createClient` capture it
   * when this module loads.
   *
   * Without this indirection the client holds whatever `fetch` existed at
   * import time, so anything that replaces the global later -- a test double,
   * or an instrumentation wrapper -- is ignored. One extra function call buys
   * a client whose transport can be substituted.
   */
  fetch: (request) => globalThis.fetch(request),
})

/**
 * The CSRF token for the current session.
 *
 * **Held in a module variable rather than React state, deliberately.** The
 * middleware below runs inside `fetch`, outside React's component tree, so it
 * cannot call a hook and cannot read component state. A module variable is the
 * plainest thing that both sides can reach.
 *
 * The cost is honest: this is mutable global state, which is normally worth
 * avoiding. It is acceptable here because exactly one writer exists
 * (`useSession` in `./session.ts`, on every load) and the value is not
 * rendered -- nothing re-renders when it changes, so React never needs to know.
 */
let csrfToken = ''

/** Called by `useSession` whenever the server tells us the current token. */
export function setCsrfToken(token: string): void {
  csrfToken = token
}

/** Exposed for tests, which assert the header is attached. */
export function currentCsrfToken(): string {
  return csrfToken
}

/**
 * Methods that do not change anything, and therefore need no CSRF token.
 *
 * This mirrors `enforce_api_csrf` (`backend/app/auth/dependencies.py`), which
 * skips the same set. CSRF defends against another site causing *your* browser
 * to perform an action as you; a request that performs no action needs no
 * defence.
 */
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])

/**
 * **The only place the CSRF header is attached.**
 *
 * Middleware here means what it means in FastAPI: a function that sees every
 * request on its way out. Putting the header here rather than at each call site
 * means there is one place to get it right, and no screen can forget it.
 *
 * The backend compares this header against a token derived from the session
 * cookie (ADR-168 point 2). The cookie itself is never touched by this code --
 * it is `httponly`, so JavaScript cannot read it, and the browser attaches it
 * automatically because the request is same-origin.
 */
client.use({
  onRequest({ request }) {
    if (!SAFE_METHODS.has(request.method.toUpperCase())) {
      request.headers.set('X-CSRF-Token', csrfToken)
    }
    return request
  },
})

export const api = client
