import { describe, it, expect } from "vitest";
import { sampleAt, toCsvRows, elapsed, type Point } from "./lookup";

describe("sampleAt (binary search)", () => {
  const pts: Point[] = [[1000, 10], [2000, 20], [3000, 30]];
  it("returns the exact sample at a matching time", () => {
    expect(sampleAt(pts, 2000)).toBe(20);
  });
  it("snaps to the nearest sample between points", () => {
    expect(sampleAt(pts, 2400)).toBe(20);
    expect(sampleAt(pts, 2600)).toBe(30);
  });
  it("returns null outside the series range", () => {
    expect(sampleAt(pts, 500)).toBeNull();
    expect(sampleAt(pts, 3500)).toBeNull();
  });
  it("returns null for an empty series", () => {
    expect(sampleAt([], 1000)).toBeNull();
  });
});

describe("toCsvRows", () => {
  it("emits a header then time-sorted rows across channels", () => {
    const rows = toCsvRows({ T1: [[2000, 20]], LOAD: [[1000, 5]] });
    expect(rows[0]).toEqual(["iso_ts", "channel", "value"]);
    expect(rows[1][1]).toBe("LOAD"); // t=1000 sorts before T1's t=2000
    expect(rows[2][1]).toBe("T1");
    expect(rows).toHaveLength(3);
  });
});

describe("elapsed", () => {
  it("formats mm:ss since burn start and clamps negatives", () => {
    expect(elapsed(0, 200_000)).toBe("t+3:20");
    expect(elapsed(1000, 1000)).toBe("t+0:00");
    expect(elapsed(5000, 0)).toBe("t+0:00");
  });
});
