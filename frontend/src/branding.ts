/**
 * What this product is called, in one place.
 *
 * **This value is provisional and the single constant is the point.** Five
 * names for this product coexist in the repository and none of them is
 * canonical:
 *
 *   - "Newsletter Reference Architecture" -- the runtime. FastAPI's title, the
 *     root route, the Jinja nav, and fossilised in the `nra_session` cookie.
 *   - "Newsletter Blueprint" -- the prose and AI-facing docs, including one
 *     string in `backend/main.py` thirty-five lines from the other name.
 *   - "Newsletter Architecture" -- CLAUDE.md's own title.
 *   - "Newsletter Reference Implementation" -- the repository and the README.
 *   - "Newsletter Manager" -- invented by this file's first author on
 *     2026-09-20 and removed the same day. It named nothing that existed.
 *
 * The name has never been decided: `docs/business/decisions/` is empty and
 * POSITIONING.md blocks beta on the positioning *statement* without ever
 * mentioning the *noun*. Naming a product is a business decision, so it is not
 * taken here.
 *
 * **The value below therefore matches what the Jinja UI already shows a
 * signed-in manager** (`backend/app/templates/base.html:18`) rather than adding
 * a sixth candidate. Matching costs nothing and inventing costs a rename.
 *
 * Tracked in `docs/backlog.md`. When the name is decided, this constant is the
 * only line in the client that changes.
 */
export const PRODUCT_NAME = 'Newsletter Reference Architecture'
