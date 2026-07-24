import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { color, space, radius, type } from "./tokens";

const css = readFileSync(
  resolve(process.cwd(), "src/tokens/tokens.css"),
  "utf-8",
);

function tokenNamesReferencedBy(group: Record<string, string>): string[] {
  return Object.values(group).map((ref) => {
    const match = /^var\((--[a-z0-9-]+)\)$/.exec(ref);
    if (!match) {
      throw new Error(`Not a var() reference: "${ref}"`);
    }
    return match[1];
  });
}

describe("tokens.ts bridge (CSS parity)", () => {
  it("every color token resolves to a real CSS custom property", () => {
    for (const name of tokenNamesReferencedBy(color)) {
      expect(css).toContain(`${name}:`);
    }
  });

  it("every space token resolves to a real CSS custom property", () => {
    for (const name of tokenNamesReferencedBy(space)) {
      expect(css).toContain(`${name}:`);
    }
  });

  it("every radius token resolves to a real CSS custom property", () => {
    for (const name of tokenNamesReferencedBy(radius)) {
      expect(css).toContain(`${name}:`);
    }
  });

  it("every type token resolves to a real CSS custom property", () => {
    for (const name of tokenNamesReferencedBy(type)) {
      expect(css).toContain(`${name}:`);
    }
  });

  it("every extended semantic-scale color token resolves to a real CSS custom property", () => {
    const extended = {
      green200: color.green200,
      green500: color.green500,
      green900: color.green900,
      amber200: color.amber200,
      amber500: color.amber500,
      amber900: color.amber900,
      red200: color.red200,
      red500: color.red500,
      red900: color.red900,
      indigo200: color.indigo200,
      indigo900: color.indigo900,
    };
    for (const name of tokenNamesReferencedBy(extended)) {
      expect(css).toContain(`${name}:`);
    }
  });
});
