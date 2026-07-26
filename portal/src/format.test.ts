import { describe, expect, it } from "vitest";
import { fmtCredit, fmtDate, fmtDateTime, fmtKg, fmtPct } from "./format";
describe("format law (audit §0.6)", () => {
  it("credits: grouped, 3 decimals", () => {
    expect(fmtCredit(646.16)).toBe("646.160");
    expect(fmtCredit(45900)).toBe("45,900.000");
    expect(fmtCredit(0)).toBe("0.000");
  });
  it("kg grouped", () => expect(fmtKg(85000)).toBe("85,000 kg"));
  it("date", () => expect(fmtDate("2026-02-02T10:05:00Z")).toBe("02 Feb 2026"));
  it("date null", () => expect(fmtDate(null)).toBe("—"));
  it("datetime", () => expect(fmtDateTime("2026-02-02T10:05:00Z")).toBe("02 Feb 2026, 10:05 UTC"));
  it("garbage in, em-dash out", () => expect(fmtDate("not-a-date")).toBe("—"));
  it("pct", () => expect(fmtPct(92.44)).toBe("92.4%"));
});
