import { describe, it, expect } from "vitest";
import { REASON_LABELS, humanizeReason } from "./blockerReasons";

describe("blockerReasons", () => {
  it("maps known codes to curated human labels", () => {
    expect(humanizeReason("missing_buyer_identity")).toBe("Missing buyer identity");
    expect(humanizeReason("assumed_h_corg")).toBe("H:Corg assumed (no lab)");
  });

  it("falls back to sentence-case for unmapped codes (never blank)", () => {
    expect(humanizeReason("some_brand_new_reason")).toBe("Some brand new reason");
    expect(humanizeReason("single")).toBe("Single");
  });

  it("every curated label is non-empty and free of underscores", () => {
    for (const [code, label] of Object.entries(REASON_LABELS)) {
      expect(label.length).toBeGreaterThan(0);
      expect(label, `label for ${code}`).not.toMatch(/_/);
    }
  });
});
