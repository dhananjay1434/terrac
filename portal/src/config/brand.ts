/** Single source of truth for the product's brand identity. Kept as the
 * exact strings already shown in the UI — this file only moves them out of
 * component code so a future white-label swap touches one place. */
export const brand = {
  wordmark: "TerraCipher",
  mark: "TC",
} as const;
