// Adds the DOM matchers (`toBeInTheDocument` and friends) to Vitest's `expect`.
import '@testing-library/jest-dom/vitest'

/**
 * Let `Request` accept a relative URL, the way a browser does.
 *
 * **This restores a browser behaviour the test environment lacks; it is not a
 * workaround for anything in the client.** jsdom does not implement `fetch`, so
 * Vitest supplies Node's, and Node's `Request` requires an absolute URL. A
 * browser resolves a relative one against the document's own address.
 *
 * The client deliberately uses relative URLs -- `baseUrl: ''` in
 * `src/api/client.ts` is what keeps it same-origin, which ADR-168 point 3 makes
 * a deployment requirement. Giving the client an absolute base URL just to make
 * tests pass would have tested a configuration that never ships.
 */
const NativeRequest = globalThis.Request

class RelativeAwareRequest extends NativeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    if (typeof input === 'string' && input.startsWith('/')) {
      input = new URL(input, window.location.origin).toString()
    }
    super(input, init)
  }
}

globalThis.Request = RelativeAwareRequest as typeof Request
