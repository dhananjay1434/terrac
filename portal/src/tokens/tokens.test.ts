import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
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
