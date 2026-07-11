import { describe, it, expect } from "vitest";
import { groupChecklist, groupOf, statusOf } from "../compliance";
import type { ChecklistItem } from "../api";

function item(p: Partial<ChecklistItem>): ChecklistItem {
  return {
    code: "c",
    section: "per-run (C1)",
    label: "l",
    ok: true,
    enforcement: "enforced",
    ...p,
  };
}

describe("groupOf", () => {
  it("maps section strings to methodology groups", () => {
    expect(groupOf(item({ section: "per-run (C1)" }))).toBe("field");
    expect(groupOf(item({ section: "lab (C7)" }))).toBe("lab");
    expect(groupOf(item({ section: "project (C8)" }))).toBe("project");
    expect(groupOf(item({ section: "annual (C9)" }))).toBe("annual");
    expect(groupOf(item({ section: "security" }))).toBe("security");
  });
});

describe("statusOf", () => {
  it("green when ok", () => {
    expect(statusOf(item({ ok: true }))).toBe("ok");
  });
  it("blocking when failed and enforced", () => {
    expect(statusOf(item({ ok: false, enforcement: "enforced" }))).toBe(
      "blocking",
    );
  });
  it("inert when failed but not enforced", () => {
    expect(statusOf(item({ ok: false, enforcement: "inert_no_linkage" }))).toBe(
      "inert",
    );
    expect(
      statusOf(item({ ok: false, enforcement: "awaiting_methodology" })),
    ).toBe("inert");
  });
});

describe("groupChecklist", () => {
  it("buckets items and counts ok/blocking per group", () => {
    const groups = groupChecklist([
      item({ code: "a", section: "per-run (C1)", ok: true }),
      item({ code: "b", section: "per-run (C2)", ok: false, enforcement: "enforced" }),
      item({ code: "c", section: "lab (C7)", ok: false, enforcement: "enforced" }),
      item({ code: "d", section: "project (C8)", ok: false, enforcement: "inert_no_linkage" }),
    ]);
    const field = groups.find((g) => g.group === "field")!;
    expect(field.items).toHaveLength(2);
    expect(field.okCount).toBe(1);
    expect(field.blockingCount).toBe(1);

    const project = groups.find((g) => g.group === "project")!;
    expect(project.blockingCount).toBe(0); // inert, not blocking

    // empty groups are omitted, and ordering follows GROUP_ORDER
    expect(groups.map((g) => g.group)).toEqual(["field", "lab", "project"]);
  });
});
