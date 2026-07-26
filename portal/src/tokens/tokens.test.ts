import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { resolve } from "node:path";

// vitest runs with cwd = portal/, so this resolves robustly regardless of
// import.meta.url quirks on Windows paths containing spaces/parentheses.
const css = readFileSync(
  resolve(process.cwd(), "src/tokens/tokens.css"),
  "utf-8",
);

describe("tokens.css", () => {
  it("defines the core semantic and action tokens", () => {
    expect(css).toContain("--action-primary-bg");
    expect(css).toContain("--surface-page");
    expect(css).toContain("--surface-card");
    expect(css).toContain("--text-primary");
  });

  it("defines a dark-theme semantic remap", () => {
    expect(css).toContain('[data-theme="dark"]');
    expect(css).toContain("--surface-page: var(--basalt-950-canvas);");
  });
});

// ── Phase 1 remediation guards (audit X1/X2/X6/X7/X8/X9) ──────────────
const root = css.slice(0, css.indexOf('[data-theme'));
const dark = css.slice(css.indexOf('[data-theme="dark"]'));

describe("dark status aliases (audit X1)", () => {
  it.each([
    "--status-success: var(--status-success-fg)",
    "--status-warning: var(--status-warning-fg)",
    "--status-error: var(--status-error-fg)",
    "--status-inert: var(--basalt-400)",
  ])("dark block remaps %s", (decl) => {
    expect(dark).toContain(decl);
  });
  it("dark hover is AA-safe", () =>
    expect(dark).toContain("--action-primary-hover: #5148e6"));
});

describe("new token scales (audit X6/X7/X8/X9)", () => {
  it.each([
    "--overlay-scrim:",
    "--overlay-scrim-strong:",
    "--r-pill:",
    "--z-modal:",
    "--z-skiplink:",
    "--control-h-md:",
    "--icon-md:",
    "--dur-spin:",
    "--dur-pulse:",
    "--scan-reticle:",
  ])("root defines %s", (name) => {
    expect(root).toContain(name);
  });
  it("dark remaps the overlay scrims", () => {
    expect(dark).toContain("--overlay-scrim: rgba(0, 0, 0, 0.6)");
    expect(dark).toContain("--overlay-scrim-strong: rgba(0, 0, 0, 0.75)");
  });
});

describe("no phantom tokens / stray scrims outside tokens.css (audit X2/X8)", () => {
  const files: string[] = [];
  (function walk(dir: string) {
    for (const name of readdirSync(dir)) {
      if (name === "node_modules" || name === "audit") continue;
      const p = resolve(dir, name);
      if (statSync(p).isDirectory()) walk(p);
      // Source only — .css/.tsx, never test files (they legitimately quote
      // these strings in assertions/descriptions).
      else if (/\.(css|tsx)$/.test(name) && !name.includes(".test.")) files.push(p);
    }
  })(resolve(process.cwd(), "src"));

  it("no var(--radius-|--border-color|--bg-card|--accent) anywhere", () => {
    const offenders: string[] = [];
    for (const f of files) {
      const t = readFileSync(f, "utf-8");
      if (/var\(--(radius-|border-color|bg-card|accent)/.test(t)) offenders.push(f);
    }
    expect(offenders).toEqual([]);
  });

  it("rgba(15, 17, 21 lives ONLY in tokens.css", () => {
    const offenders: string[] = [];
    for (const f of files) {
      if (f.endsWith("tokens.css")) continue;
      if (/rgba\(15, 17, 21/.test(readFileSync(f, "utf-8"))) offenders.push(f);
    }
    expect(offenders).toEqual([]);
  });
});
