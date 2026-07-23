import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import EvidenceGallery from "./EvidenceGallery";
import type { MediaItem } from "../../api";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return {
    ...actual,
    fetchMediaUrl: vi.fn().mockResolvedValue("blob:mock"),
    verifyMedia: vi.fn(),
  };
});
vi.mock("../../auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../auth")>();
  return { ...actual, getRole: () => "admin" };
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
    verification_status: null,
    verification_remarks: null,
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

  it("renders a <video> thumbnail for a video item and an <img> for a photo", async () => {
    const withVideo = [
      ...ITEMS,
      media({ operation_id: "o5", sha256_hash: "h5", capture_type: "quenching_video", filename: "quenching.mp4" }),
    ];
    const { container } = render(<EvidenceGallery media={withVideo} />);
    const openBtn = await screen.findByRole("button", { name: "Open evidence h5" });
    expect(openBtn.querySelector("video")).not.toBeNull();
    const photoBtn = screen.getByRole("button", { name: "Open evidence h2" });
    expect(photoBtn.querySelector("img")).not.toBeNull();
    expect(photoBtn.querySelector("video")).toBeNull();
    void container;
  });

  it("video thumbnail becomes visible on loadeddata (not load)", async () => {
    const withVideo = [
      media({ operation_id: "ov", sha256_hash: "hv", capture_type: "quenching_video", filename: "quenching.mp4" }),
    ];
    render(<EvidenceGallery media={withVideo} />);
    const openBtn = await screen.findByRole("button", { name: "Open evidence hv" });
    const video = openBtn.querySelector("video") as HTMLVideoElement;
    expect(video.className).not.toContain("loaded");
    fireEvent.loadedData(video);
    expect(video.className).toContain("loaded");
  });
});

describe("EvidenceGallery — reviewer verdict (V8 Part 4 K)", () => {
  beforeEach(() => vi.clearAllMocks());

  function cellFor(sha: string) {
    const openBtn = screen.getByRole("button", { name: `Open evidence ${sha}` });
    return within(openBtn.closest(".media-cell") as HTMLElement);
  }

  it("approves a media item and shows the verdict chip immediately", async () => {
    const { verifyMedia } = await import("../../api");
    vi.mocked(verifyMedia).mockResolvedValue({
      operation_id: "o1",
      verification_status: "approved",
      verification_remarks: null,
    });
    render(<EvidenceGallery media={ITEMS} />);

    fireEvent.click(cellFor("h1").getByRole("button", { name: "Approve" }));

    expect(
      await cellFor("h1").findByText("reviewer approved"),
    ).toBeInTheDocument();
    expect(verifyMedia).toHaveBeenCalledWith("o1", { status: "approved" });
  });

  it("rejects a media item with a reason and shows it inline", async () => {
    const { verifyMedia } = await import("../../api");
    vi.mocked(verifyMedia).mockResolvedValue({
      operation_id: "o1",
      verification_status: "rejected",
      verification_remarks: "kiln ID not visible",
    });
    render(<EvidenceGallery media={ITEMS} />);

    fireEvent.click(cellFor("h1").getByRole("button", { name: "Reject" }));
    fireEvent.change(screen.getByLabelText("Rejection reason for o1"), {
      target: { value: "kiln ID not visible" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirm reject" }));

    expect(
      await cellFor("h1").findByText(/rejected: kiln ID not visible/),
    ).toBeInTheDocument();
    expect(verifyMedia).toHaveBeenCalledWith("o1", {
      status: "rejected",
      remarks: "kiln ID not visible",
    });
  });
});
