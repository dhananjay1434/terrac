import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ComplianceChecklist from "../components/ComplianceChecklist";
import type { ChecklistItem } from "../api";

const checklist: ChecklistItem[] = [
  { code: "a", section: "per-run (C1)", label: "Biomass input", ok: true, enforcement: "enforced" },
  { code: "b", section: "per-run (C3)", label: "Pyrolysis photos", ok: false, enforcement: "enforced" },
  { code: "c", section: "lab (C7)", label: "H:Corg", ok: false, enforcement: "enforced" },
];

describe("<ComplianceChecklist />", () => {
  it("renders grouped sections with per-item labels", () => {
    render(<ComplianceChecklist checklist={checklist} />);
    expect(screen.getByTestId("group-field")).toBeInTheDocument();
    expect(screen.getByTestId("group-lab")).toBeInTheDocument();
    expect(screen.getByText("Biomass input")).toBeInTheDocument();
    expect(screen.getByText("Pyrolysis photos")).toBeInTheDocument();
    expect(screen.getByText("H:Corg")).toBeInTheDocument();
  });

  it("marks a failed enforced item as blocking (MISSING)", () => {
    render(<ComplianceChecklist checklist={checklist} />);
    const missing = screen.getAllByText("MISSING");
    expect(missing.length).toBe(2); // pyrolysis photos + H:Corg
  });
});
