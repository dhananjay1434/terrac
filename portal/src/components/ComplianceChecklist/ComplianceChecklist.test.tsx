import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ComplianceChecklist from "./ComplianceChecklist";
import type { ChecklistItem } from "../../api";

// Real compliance.ts module — mocking it is not allowed for this suite.
const checklist: ChecklistItem[] = [
  { code: "C1a", section: "per-run (C1)", label: "Biomass input", ok: true, enforcement: "enforced" },
  { code: "C3a", section: "per-run (C3)", label: "Pyrolysis photos", ok: false, enforcement: "enforced" },
  { code: "C4a", section: "per-run (C4)", label: "Flag-gated extra", ok: false, enforcement: "flag-gated" },
  { code: "C7a", section: "lab (C7)", label: "H:Corg", ok: false, enforcement: "enforced" },
  { code: "SEC", section: "security", label: "Device key attested", ok: true, enforcement: "enforced" },
];

describe("ComplianceChecklist (grouped accordion)", () => {
  it("renders sections in GROUP_ORDER", () => {
    const { container } = render(<ComplianceChecklist checklist={checklist} />);
    const ids = Array.from(
      container.querySelectorAll("[data-testid^='group-']"),
    ).map((el) => el.getAttribute("data-testid"));
    expect(ids).toEqual(["group-field", "group-lab", "group-security"]);
  });

  it("sorts blocking items first within a group", () => {
    render(<ComplianceChecklist checklist={checklist} />);
    const fieldRows = Array.from(
      screen.getByTestId("group-field").querySelectorAll("li"),
    ).map((li) => li.getAttribute("data-status"));
    expect(fieldRows).toEqual(["blocking", "inert", "ok"]);
  });

  it("shows correct counts in the group header", () => {
    render(<ComplianceChecklist checklist={checklist} />);
    const field = screen.getByTestId("group-field");
    expect(field.textContent).toContain("1 ok");
    expect(field.textContent).toContain("1 missing");
    expect(field.textContent).toContain("1 n/a");
  });
});
