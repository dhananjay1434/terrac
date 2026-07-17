// Axe audit over every page render, WCAG 2.x A/AA rulesets. jsdom cannot
// compute color-contrast (no layout engine) — axe marks those checks
// "incomplete" rather than violations; contrast is enforced by the token
// design (every fg/bg pair documented in styles.css passes ≥4.5:1).
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import * as Tooltip from "@radix-ui/react-tooltip";
import { axe } from "jest-axe";
import AppShell from "../components/AppShell/AppShell";
import Login from "../pages/Login";
import Batches from "../pages/Batches";
import BatchDetail from "../pages/BatchDetail";
import LabScan from "../pages/LabScan";
import LabEntry from "../pages/LabEntry";
import Registry from "../pages/Registry";
import type { BatchDetail as Detail, BatchRow } from "../api";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    login: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    listBatches: vi.fn(),
    getBatch: vi.fn(),
    fetchMediaUrl: vi.fn().mockResolvedValue("blob:mock"),
    issueCredit: vi.fn(),
    listKilns: vi.fn().mockResolvedValue({ kilns: [] }),
    mintToken: vi.fn(),
    registryPost: vi.fn().mockResolvedValue({}),
  };
});
vi.mock("../auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../auth")>();
  return { ...actual, getRole: () => "admin", isAuthed: () => true };
});

import { listBatches, getBatch } from "../api";

const UUID = "aaaa1111-2222-3333-4444-555566667777";
const ROW: BatchRow = {
  batch_uuid: UUID,
  device_id: "dev-1",
  project_id: "p1",
  status: "RECEIVED",
  provisional: true,
  reason_count: 2,
  net_credit_t_co2e: 1.234,
  wet_yield_kg: 100,
  received_at: "2026-07-01T10:00:00Z",
};
const DETAIL: Detail = {
  batch: ROW,
  compliance: {
    batch_uuid: UUID,
    provisional: true,
    issuable: false,
    reasons: ["a", "b"],
    checklist: [
      { code: "C1a", section: "per-run (C1)", label: "Biomass input", ok: true, enforcement: "enforced" },
      { code: "C7a", section: "lab (C7)", label: "H:Corg", ok: false, enforcement: "enforced" },
    ],
  },
  evidence_counts: { moisture_readings: 3 },
  media: [
    {
      operation_id: "op1",
      filename: null,
      sha256_hash: "f00dfeedface1234",
      uploaded_at: "2026-07-01T10:00:00Z",
      capture_type: "flame_curtain",
      capture_type_verified: true,
      exif_lat: 12.3,
      exif_lon: 76.5,
    },
  ],
};

const AXE_OPTS = {
  runOnly: { type: "tag" as const, values: ["wcag2a", "wcag2aa"] },
};

async function expectNoViolations(container: HTMLElement) {
  const results = await axe(container, AXE_OPTS);
  expect(results.violations).toEqual([]);
}

describe("a11y (axe, WCAG 2.x A/AA)", () => {
  beforeEach(() => {
    vi.mocked(listBatches).mockResolvedValue({ batches: [ROW], next_cursor: null });
    vi.mocked(getBatch).mockResolvedValue(DETAIL);
  });

  it("Login", async () => {
    const { container } = render(
      <MemoryRouter><main><Login /></main></MemoryRouter>,
    );
    await expectNoViolations(container);
  }, 20000);

  it("AppShell", async () => {
    const { container } = render(
      <MemoryRouter><AppShell><div>content</div></AppShell></MemoryRouter>,
    );
    await expectNoViolations(container);
  }, 20000);

  it("Batches", async () => {
    const { container } = render(
      <MemoryRouter>
        <Tooltip.Provider>
          <main><Batches /></main>
        </Tooltip.Provider>
      </MemoryRouter>,
    );
    await screen.findByText("dev-1");
    await expectNoViolations(container);
  }, 20000);

  it("BatchDetail", async () => {
    const { container } = render(
      <MemoryRouter initialEntries={[`/batches/${UUID}`]}>
        <main>
          <Routes>
            <Route path="/batches/:uuid" element={<BatchDetail />} />
          </Routes>
        </main>
      </MemoryRouter>,
    );
    await screen.findByText("PROVISIONAL");
    await expectNoViolations(container);
  }, 20000);

  it("LabScan", async () => {
    const { container } = render(
      <MemoryRouter><main><LabScan /></main></MemoryRouter>,
    );
    await expectNoViolations(container);
  }, 20000);

  it("LabEntry", async () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/lab/abc"]}>
        <Tooltip.Provider>
          <main>
            <Routes>
              <Route path="/lab/:uuid" element={<LabEntry />} />
            </Routes>
          </main>
        </Tooltip.Provider>
      </MemoryRouter>,
    );
    await expectNoViolations(container);
  }, 20000);

  it("Registry", async () => {
    const { container } = render(
      <MemoryRouter>
        <Tooltip.Provider>
          <main><Registry /></main>
        </Tooltip.Provider>
      </MemoryRouter>,
    );
    await expectNoViolations(container);
  }, 20000);
});
