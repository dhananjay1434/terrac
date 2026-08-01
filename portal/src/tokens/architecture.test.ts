import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";

// Permanent guards (UX-G1) so the UI/UX consolidation (ChartFrame, DataTable,
// feature hooks) can't silently rot back into god-pages / hand-rolled markup.

const PAGES_DIR = resolve(process.cwd(), "src/pages");

function pageFiles(): string[] {
  return readdirSync(PAGES_DIR)
    .filter((n) => n.endsWith(".tsx") && !n.includes(".test."))
    .map((n) => resolve(PAGES_DIR, n));
}

describe("no raw <table> in pages — use DataTable (UX-G1)", () => {
  it("every page composes DataTable instead of hand-rolling <table>", () => {
    const offenders: string[] = [];
    for (const f of pageFiles()) {
      if (/<table\b/.test(readFileSync(f, "utf8"))) offenders.push(f);
    }
    expect(offenders, `move these into DataTable:\n${offenders.join("\n")}`).toEqual([]);
  });
});

describe("no hand-drawn chart marks in pages — use a ui/*Chart* component (UX-G1)", () => {
  it("no page draws <polyline> or a filled <rect> directly", () => {
    const offenders: string[] = [];
    for (const f of pageFiles()) {
      const t = readFileSync(f, "utf8");
      if (/<polyline\b/.test(t) || /<rect\b[^>]*\bfill=/.test(t)) offenders.push(f);
    }
    expect(offenders, `move chart marks into a ui/*Chart* component:\n${offenders.join("\n")}`).toEqual([]);
  });
});

describe("de-godded pages fetch only through their feature hook (UX-G1/D1)", () => {
  // These 3 were the audited god-pages (436/401/392 lines) split into
  // src/features/*/useX.ts — guard that the split can't quietly regress.
  const DEGODDED = ["Dispatch.tsx", "BatchDetail.tsx", "Projects.tsx"];

  it.each(DEGODDED)("%s imports no data-fetch function from api/api2 directly", (name) => {
    const src = readFileSync(resolve(PAGES_DIR, name), "utf8");
    const apiImport = src.match(/import\s*\{([^}]*)\}\s*from\s*["']\.\.\/api2?["']/g) ?? [];
    const offenders = apiImport
      .join("\n")
      .split(",")
      .map((s) => s.trim())
      .filter((s) => /^(get|list|create|update|delete|issue|download|bind)[A-Z]/.test(s));
    expect(offenders, `${name} should fetch via its useX feature hook, not: ${offenders.join(", ")}`).toEqual([]);
  });
});
