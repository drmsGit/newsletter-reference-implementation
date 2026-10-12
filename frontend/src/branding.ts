/**
 * What this product is called, in one place.
 *
 * **The name is a neutral working title (2026-10-12) until a brand is chosen**
 * (`docs/business/decisions/naming-brand-tarrow.md`) — so it is not written
 * here. It comes from `product.json` at the repository root, which the backend
 * reads too, through `vite.config.ts` (task-29). A rename changes that file and
 * runs `backend/scripts/rename_product.py`; this file does not change.
 */
export const PRODUCT_NAME: string = __PRODUCT_NAME__
