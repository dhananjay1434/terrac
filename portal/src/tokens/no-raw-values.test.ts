import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, basename, resolve } from "node:path";

// Permanent guard (P8.5): the design system is token-only. Raw spacing px on
// padding/margin/gap and raw hex colors must not creep back into CSS. If this
// fails, replace the flagged literal with the matching token (see tokens.css:
// --space-*, the color scales) — never silence the test.

// vitest runs with cwd = portal/, matching tokens.test.ts (robust on Windows
// paths with spaces/parentheses where import.meta.url misbehaves).
const SRC = resolve(process.cwd(), "src");

function cssFiles(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...cssFiles(p));
    else if (name.endsWith(".module.css") || name === "styles.css") out.push(p);
  }
  return out;
}

// Off-scale + on-scale-but-should-be-a-token spacing values (Global Rule 8).
const SPACING_RE =
  /(padding|margin|gap)[\w-]*\s*:[^;}]*\b(2|6|9|10|14|18|20|28|40|60)px/;
const HEX_RE = /#[0-9a-fA-F]{3,8}\b/;

const FILES = cssFiles(SRC);
// tokens.css is the single source of raw values and is not a *.module.css /
// styles.css, so it is already outside FILES. Logo art is allowlisted.
const HEX_ALLOWLIST = new Set(["Logo.module.css"]);

describe("no raw design values in CSS (P8.5 guard)", () => {
  it("uses spacing tokens, not raw px, on padding/margin/gap", () => {
    const hits: string[] = [];
    for (const f of FILES) {
      readFileSync(f, "utf8")
        .split("\n")
        .forEach((line, i) => {
          if (SPACING_RE.test(line)) hits.push(`${f}:${i + 1}: ${line.trim()}`);
        });
    }
    expect(hits, `raw spacing px found:\n${hits.join("\n")}`).toEqual([]);
  });

  it("uses color tokens, not hex literals", () => {
    const hits: string[] = [];
    for (const f of FILES) {
      if (HEX_ALLOWLIST.has(basename(f))) continue;
      readFileSync(f, "utf8")
        .split("\n")
        .forEach((line, i) => {
          if (line.includes("data:image")) return;
          if (HEX_RE.test(line)) hits.push(`${f}:${i + 1}: ${line.trim()}`);
        });
    }
    expect(hits, `raw hex colors found:\n${hits.join("\n")}`).toEqual([]);
  });
});
