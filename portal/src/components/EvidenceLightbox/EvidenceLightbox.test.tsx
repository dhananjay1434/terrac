import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import EvidenceLightbox from "./EvidenceLightbox";
import type { MediaItem } from "../../api";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return { ...actual, fetchMediaUrl: vi.fn().mockResolvedValue("blob:mock") };
});

const ITEMS: MediaItem[] = [0, 1, 2].map((i) => ({
  operation_id: `op${i}`,
  filename: null,
  sha256_hash: `hash-${i}-abcdef1234567890`,
  uploaded_at: "2026-07-01T10:00:00Z",
  capture_type: "flame_curtain",
  capture_type_verified: true,
  exif_lat: 12.34567,
  exif_lon: 76.54321,
  verification_status: null,
  verification_remarks: null,
}));

describe("EvidenceLightbox", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows the full hash, GPS, timestamp and verification state", () => {
    render(
      <EvidenceLightbox
        items={ITEMS}
        index={0}
        onClose={vi.fn()}
        onNavigate={vi.fn()}
      />,
    );
    expect(screen.getByText("hash-0-abcdef1234567890")).toBeInTheDocument();
    expect(screen.getByText("12.34567, 76.54321")).toBeInTheDocument();
    expect(screen.getByText("2026-07-01 10:00")).toBeInTheDocument();
    expect(screen.getByText("✓ verified")).toBeInTheDocument();
  });

  it("traps focus inside the dialog", () => {
    render(
      <EvidenceLightbox
        items={ITEMS}
        index={0}
        onClose={vi.fn()}
        onNavigate={vi.fn()}
      />,
    );
    const dialog = screen.getByRole("dialog");
    expect(dialog.contains(document.activeElement)).toBe(true);
    fireEvent.keyDown(document.activeElement!, { key: "Tab" });
    expect(dialog.contains(document.activeElement)).toBe(true);
  });

  it("Escape closes via onClose", () => {
    const onClose = vi.fn();
    render(
      <EvidenceLightbox
        items={ITEMS}
        index={0}
        onClose={onClose}
        onNavigate={vi.fn()}
      />,
    );
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("arrow keys navigate within bounds", () => {
    const onNavigate = vi.fn();
    render(
      <EvidenceLightbox
        items={ITEMS}
        index={1}
        onClose={vi.fn()}
        onNavigate={onNavigate}
      />,
    );
    const dialog = screen.getByRole("dialog");
    fireEvent.keyDown(dialog, { key: "ArrowRight" });
    expect(onNavigate).toHaveBeenCalledWith(2);
    fireEvent.keyDown(dialog, { key: "ArrowLeft" });
    expect(onNavigate).toHaveBeenCalledWith(0);
  });
});
