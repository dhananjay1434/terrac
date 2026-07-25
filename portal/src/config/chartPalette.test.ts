import { describe, it, expect } from "vitest";
import { INDIGO_CHART_SCALE, indigoTone } from "./chartPalette";

describe("chartPalette", () => {
  it("every stop is a real indigo token reference, never a raw hex", () => {
    for (const tone of INDIGO_CHART_SCALE) {
      expect(tone).toMatch(/^var\(--indigo-\d+\)$/);
    }
  });

  it("returns tones by index", () => {
    expect(indigoTone(0)).toBe(INDIGO_CHART_SCALE[0]);
    expect(indigoTone(3)).toBe(INDIGO_CHART_SCALE[3]);
  });

  it("cycles once the index exceeds the scale length", () => {
    expect(indigoTone(INDIGO_CHART_SCALE.length)).toBe(INDIGO_CHART_SCALE[0]);
  });
});
