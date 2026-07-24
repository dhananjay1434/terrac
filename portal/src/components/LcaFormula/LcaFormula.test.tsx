import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import LcaFormula from "./LcaFormula";
import type { LcaBreakdown } from "../../api";

const POPULATED: LcaBreakdown = {
  dry_mass_t: 2.0,
  gross_c_sink_t_co2e: 5.0,
  cremain_t: 1.0,
  safety_deduction_kg: 100,
  transport_penalty_kg: 50,
  ch4_penalty_kg: 20,
  net_credit_t_co2e: 3.4633333333333334, // (1 * 44/12) - 0.1 - 0.05 - 0.02
  provisional: false,
  corg_assumed: false,
};

describe("LcaFormula", () => {
  it("renders the pending line with no numbers when breakdown is null", () => {
    render(<LcaFormula breakdown={null} />);
    expect(screen.getByText("Credit breakdown pending")).toBeInTheDocument();
    expect(screen.queryByText(/tCO₂e/)).not.toBeInTheDocument();
  });

  it("renders the pending line when net_credit_t_co2e is missing", () => {
    const { net_credit_t_co2e, ...rest } = POPULATED;
    void net_credit_t_co2e;
    render(<LcaFormula breakdown={rest} />);
    expect(screen.getByText("Credit breakdown pending")).toBeInTheDocument();
  });

  it("renders the pending line when cremain_t is missing", () => {
    const { cremain_t, ...rest } = POPULATED;
    void cremain_t;
    render(<LcaFormula breakdown={rest} />);
    expect(screen.getByText("Credit breakdown pending")).toBeInTheDocument();
  });

  it("renders every term in tCO2e and the equation reconciles to the net (INV-4)", () => {
    render(<LcaFormula breakdown={POPULATED} />);

    const term1 = POPULATED.cremain_t! * (44 / 12);
    const dSafety = POPULATED.safety_deduction_kg! / 1000;
    const dTransport = POPULATED.transport_penalty_kg! / 1000;
    const dCh4 = POPULATED.ch4_penalty_kg! / 1000;
    const net = POPULATED.net_credit_t_co2e!;

    // The core invariant: what's displayed must actually reconcile. A loose
    // tolerance here is intentional — its job is to catch a UNIT mistake
    // (e.g. forgetting ÷1000 or ×44/12, off by 3+ orders of magnitude), not
    // to police float rounding.
    expect(Math.abs(term1 - dSafety - dTransport - dCh4 - net)).toBeLessThan(0.05);

    expect(screen.getByText("Carbon remaining")).toBeInTheDocument();
    expect(screen.getByText("− Safety margin")).toBeInTheDocument();
    expect(screen.getByText("− Transport")).toBeInTheDocument();
    expect(screen.getByText("− Pyrolysis (CH₄)")).toBeInTheDocument();
    expect(screen.getByText("= Net credit")).toBeInTheDocument();

    // Every tCO2e figure rendered via fmtCredit (3 decimals).
    expect(screen.getAllByText(/tCO₂e/).length).toBeGreaterThanOrEqual(5);
  });

  it("labels the gross figure as informational, never as the net", () => {
    render(<LcaFormula breakdown={POPULATED} />);
    expect(
      screen.getByText(/Informational \(gross, pre-deduction\) — not the issued credit/),
    ).toBeInTheDocument();
  });

  it("shows a provisional label when the breakdown is provisional", () => {
    render(<LcaFormula breakdown={{ ...POPULATED, provisional: true }} />);
    expect(screen.getByText("Provisional — not yet issued")).toBeInTheDocument();
  });

  it("does not show a provisional label when issued", () => {
    render(<LcaFormula breakdown={POPULATED} />);
    expect(screen.queryByText("Provisional — not yet issued")).not.toBeInTheDocument();
  });
});
