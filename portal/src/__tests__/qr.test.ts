import { describe, it, expect } from "vitest";
import { kilnQrPayload, enrollQrPayload } from "../qr";

// These are cross-system contracts (the mobile app parses them) — pin them.
describe("qr payloads", () => {
  it("kiln QR matches dmrv-kiln:v1 (P1-S3)", () => {
    expect(kilnQrPayload({ kiln_id: "KILN-42", kiln_type: "open", capacity_l: 200 })).toBe(
      'dmrv-kiln:v1:{"kiln_id":"KILN-42","kiln_type":"open","capacity_l":200}',
    );
  });

  it("kiln QR emits null capacity when absent", () => {
    expect(kilnQrPayload({ kiln_id: "K1", kiln_type: "closed" })).toBe(
      'dmrv-kiln:v1:{"kiln_id":"K1","kiln_type":"closed","capacity_l":null}',
    );
  });

  it("enrollment QR matches dmrv-enroll:v1 (P1-S8)", () => {
    expect(enrollQrPayload({ url: "https://api.example", token: "T0k" })).toBe(
      'dmrv-enroll:v1:{"url":"https://api.example","token":"T0k"}',
    );
  });
});
