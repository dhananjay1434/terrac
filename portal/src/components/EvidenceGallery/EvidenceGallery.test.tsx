import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import EvidenceGallery from "./EvidenceGallery";
import type { MediaItem } from "../../api";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return { ...actual, fetchMediaUrl: vi.fn().mockResolvedValue("blob:mock") };
});

function media(over: Partial<MediaItem>): MediaItem {
  return {
    operation_id: "op",
    filename: null,
    sha256_hash: "hash",
    uploaded_at: null,
    capture_type: null,
    capture_type_verified: false,
    exif_lat: null,
    exif_lon: null,
    ...over,
  };
}

const ITEMS: MediaItem[] = [
  media({ operation_id: "o1", sha256_hash: "h1", capture_type: "0" }),
  media({ operation_id: "o2", sha256_hash: "h2", capture_type: "flame_curtain", capture_type_verified: true }),
  media({ operation_id: "o3", sha256_hash: "h3", capture_type: "lab_certificate", filename: "cert.pdf" }),
];

describe("EvidenceGallery", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders numbered chapters in STEP_ORDER; empty chapters absent", () => {
    render(<EvidenceGallery media={ITEMS} />);
    const headings = screen
      .getAllByRole("heading", { level: 3 })
      .map((h) => h.textContent);
    expect(headings[0]).toContain("1. Burn — flame curtain");
    expect(headings[1]).toContain("2. Smoke opacity — 0%");
    expect(headings[2]).toContain("3. Lab certificate");
    expect(screen.queryByText(/Smoke opacity — 50%/)).not.toBeInTheDocument();
  });

  it("renders a source-stamped end_use photo under its own named section, not Other", () => {
    const withEndUse = [
      ...ITEMS,
      media({ operation_id: "o4", sha256_hash: "h4", capture_type: "end_use" }),
    ];
    render(<EvidenceGallery media={withEndUse} />);
    expect(
      screen.getByRole("heading", {
        level: 3,
        name: /End use — field application/,
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Other \/ Uncategorized/)).not.toBeInTheDocument();
  });

  it("filter tabs narrow the visible chapters client-side", () => {
    render(<EvidenceGallery media={ITEMS} />);
    fireEvent.click(screen.getByRole("tab", { name: "Certificates" }));
    expect(screen.getByText(/Lab certificate/)).toBeInTheDocument();
    expect(screen.queryByText(/flame curtain/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Photos" }));
    expect(screen.queryByText(/Lab certificate/)).not.toBeInTheDocument();
    expect(screen.getByText(/flame curtain/)).toBeInTheDocument();
  });

  it("renders nothing when there is no media", () => {
    const { container } = render(<EvidenceGallery media={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("opens the lightbox on cell click", async () => {
    render(<EvidenceGallery media={ITEMS} />);
    fireEvent.click(screen.getByRole("button", { name: "Open evidence h2" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("SHA-256")).toBeInTheDocument();
  });
});
