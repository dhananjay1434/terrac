import { describe, it, expect } from "vitest";
import { parseBatchQr, validateLabForm, type LabForm } from "../lab";

const U = "abcdef12-3456-7890-abcd-ef1234567890";

describe("parseBatchQr", () => {
  it("extracts the uuid from a dmrv-batch:v1 card", () => {
    expect(parseBatchQr(`dmrv-batch:v1:${U}`)).toBe(U);
  });
  it("rejects the wrong prefix or a bad uuid", () => {
    expect(parseBatchQr(`dmrv-enroll:v1:${U}`)).toBeNull();
    expect(parseBatchQr("dmrv-batch:v1:not-a-uuid")).toBeNull();
    expect(parseBatchQr("random text")).toBeNull();
  });
});

function form(p: Partial<LabForm>): LabForm {
  return {
    lab_h_corg: "",
    organic_carbon_pct: "",
    biochar_moisture_samples: "",
    dry_bulk_density: "",
    ...p,
  };
}

describe("validateLabForm", () => {
  it("builds a body from only the filled fields", () => {
    const { errors, body } = validateLabForm(
      form({ lab_h_corg: "0.5", organic_carbon_pct: "0.6" }),
    );
    expect(errors).toEqual([]);
    expect(body).toEqual({ lab_h_corg: 0.5, organic_carbon_pct: 0.6 });
  });

  it("flags out-of-range H:Corg and Corg", () => {
    expect(validateLabForm(form({ lab_h_corg: "2.0" })).errors.length).toBe(1);
    expect(
      validateLabForm(form({ organic_carbon_pct: "1.4" })).errors.length,
    ).toBe(1);
  });

  it("requires >=3 valid moisture samples", () => {
    expect(
      validateLabForm(form({ biochar_moisture_samples: "8, 9" })).errors,
    ).toContain("Provide at least 3 biochar moisture samples.");
    const ok = validateLabForm(form({ biochar_moisture_samples: "8, 9, 10" }));
    expect(ok.errors).toEqual([]);
    expect(ok.body.biochar_moisture_samples).toEqual([8, 9, 10]);
  });

  it("requires at least one field", () => {
    expect(validateLabForm(form({})).errors).toContain(
      "Enter at least one lab result.",
    );
  });
});
