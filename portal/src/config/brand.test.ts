import { describe, it, expect } from "vitest";
import { brand } from "./brand";

describe("brand config", () => {
  it("has a non-empty wordmark and mark", () => {
    expect(brand.wordmark.length).toBeGreaterThan(0);
    expect(brand.mark.length).toBeGreaterThan(0);
  });

  it("matches the values currently shown in the UI", () => {
    expect(brand.wordmark).toBe("TerraCipher");
    expect(brand.mark).toBe("TC");
  });
});
