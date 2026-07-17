import { describe, it, expect } from "vitest";
import { fmtCredit } from "../format";

describe("fmtCredit", () => {
  it("renders 3 decimal places", () => {
    expect(fmtCredit(1.2)).toBe("1.200");
    expect(fmtCredit(1.2346)).toBe("1.235");
    expect(fmtCredit(0)).toBe("0.000");
  });
});
