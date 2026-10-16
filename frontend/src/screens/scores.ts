/** A category score's choices: 1 (barely in the category) to 10 (squarely), ADR-080's 2026-10-04 addendum. */
export const SCORES = Array.from({ length: 10 }, (_, index) => ({ id: String(index + 1), name: String(index + 1) }))
