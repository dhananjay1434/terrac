import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { resolve } from "node:path";

// Permanent guards (UX-G2): icon-only interactive controls must be reachable
// by name for screen-reader / voice-control users; a bare aria-hidden icon
// as a button's only content is otherwise silent.

const SRC = resolve(process.cwd(), "src");

function tsxFiles(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = resolve(dir, name);
    if (statSync(p).isDirectory()) out.push(...tsxFiles(p));
    else if (name.endsWith(".tsx") && !name.includes(".test.")) out.push(p);
  }
  return out;
}

const FILES = tsxFiles(SRC);

describe("icon-only buttons have an accessible name (UX-G2)", () => {
  it("every <button> whose only child is an aria-hidden icon carries aria-label/aria-labelledby", () => {
    const offenders: string[] = [];
    for (const f of FILES) {
      const src = readFileSync(f, "utf8");
      // Match <button ...>...</button> blocks (non-greedy, single-nesting —
      // sufficient for this codebase's flat icon-button markup).
      const buttonRe = /<button\b([^>]*)>([\s\S]*?)<\/button>/g;
      let m: RegExpExecArray | null;
      while ((m = buttonRe.exec(src))) {
        const [, attrs, body] = m;
        const hasLabel = /aria-label\s*=|aria-labelledby\s*=/.test(attrs);
        if (hasLabel) continue;
        // Body is icon-only when it contains an aria-hidden element and no
        // other visible text/JSX-expression content alongside it.
        const withoutIcon = body.replace(/<[A-Za-z][\w.]*[^>]*aria-hidden[^>]*\/?>/g, "");
        const hasVisibleContent = /\S/.test(withoutIcon.replace(/\{\s*\/\*[\s\S]*?\*\/\s*\}/g, ""));
        const hasIcon = /aria-hidden/.test(body);
        if (hasIcon && !hasVisibleContent) {
          offenders.push(`${f}: <button> with only an aria-hidden icon has no aria-label`);
        }
      }
    }
    expect(offenders, offenders.join("\n")).toEqual([]);
  });
});
