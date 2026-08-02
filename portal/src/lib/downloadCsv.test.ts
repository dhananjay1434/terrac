import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { downloadCsv } from "./downloadCsv";

describe("downloadCsv", () => {
  const createObjectURL = vi.fn((_b: Blob) => "blob:mock-url");
  const revokeObjectURL = vi.fn();

  beforeEach(() => {
    createObjectURL.mockClear();
    revokeObjectURL.mockClear();
    // jsdom does not implement these.
    (URL as unknown as { createObjectURL: typeof createObjectURL }).createObjectURL = createObjectURL;
    (URL as unknown as { revokeObjectURL: typeof revokeObjectURL }).revokeObjectURL = revokeObjectURL;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates a blob, triggers an anchor download, and revokes the url", () => {
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    downloadCsv("burn.csv", [
      ["iso_ts", "channel", "value"],
      ["2026-01-01T00:00:00.000Z", "T1", "412.5"],
    ]);

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    const blobArg = createObjectURL.mock.calls[0][0] as Blob;
    expect(blobArg.type).toBe("text/csv;charset=utf-8");
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });

  it("quotes cells containing commas, quotes, or newlines (RFC-4180)", () => {
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const OriginalBlob = globalThis.Blob;
    let capturedParts: string[] = [];
    class CapturingBlob extends OriginalBlob {
      constructor(parts: string[], opts?: BlobPropertyBag) {
        super(parts, opts);
        capturedParts = parts;
      }
    }
    globalThis.Blob = CapturingBlob as unknown as typeof Blob;

    downloadCsv("x.csv", [["a,b", 'has"quote', "line\nbreak"]]);

    globalThis.Blob = OriginalBlob;
    const text = capturedParts.join("");
    expect(text).toContain('"a,b"');
    expect(text).toContain('"has""quote"');
    expect(text).toContain('"line\nbreak"');
  });
});
