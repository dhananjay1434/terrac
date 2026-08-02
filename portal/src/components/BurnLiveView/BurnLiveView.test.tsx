import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import BurnLiveView, { appendFrame } from "./BurnLiveView";
import type { ThermalMapData } from "../../ui/ThermalMapChart/ThermalMapChart";

function snapshot(): ThermalMapData {
  return {
    channels: { T1: { points: [[1000, 400]], max: 400, min: 400 } },
    burn: { t_start: 1000, t_end: 1000 },
  };
}

function snapshotWithLoad(): ThermalMapData {
  return {
    channels: {
      T1: { points: [[1000, 400], [11000, 420]], max: 420, min: 400 },
      LOAD: { points: [[1000, 5], [11000, 15]], max: 15, min: 5 },
    },
    burn: { t_start: 1000, t_end: 11000 },
  };
}

describe("appendFrame (pure)", () => {
  it("appends stream points to the right channel and extends the burn end", () => {
    const out = appendFrame(snapshot(), {
      channel: "T1",
      t_start: 2000,
      sample_period_s: 10,
      values: [410, 420],
    });
    expect(out.channels.T1.points).toHaveLength(3);
    expect(out.channels.T1.max).toBe(420);
    expect(out.burn.t_end).toBe(2000 + 10000); // last appended ts
  });

  it("creates a channel that wasn't in the snapshot (e.g. LOAD arrives later)", () => {
    const out = appendFrame(snapshot(), {
      channel: "LOAD",
      t_start: 1000,
      sample_period_s: 10,
      values: [50],
    });
    expect(out.channels.LOAD.points).toHaveLength(1);
    expect(out.channels.T1.points).toHaveLength(1); // untouched
  });
});

describe("BurnLiveView", () => {
  it("renders the thermal chart for a static snapshot, no LIVE badge", () => {
    const { container, queryByText } = render(
      <BurnLiveView uuid="b1" initial={snapshot()} live={false} />,
    );
    expect(container.querySelector("polyline")).not.toBeNull();
    expect(queryByText("LIVE")).toBeNull();
  });

  it("tier-aware: empty channels → renders null (BatchDetail falls back)", () => {
    const { container } = render(
      <BurnLiveView uuid="b1" initial={{ channels: {}, burn: { t_start: 0, t_end: 0 } }} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("opens the stream when live and appends frames in real time", async () => {
    let emit: (m: { type: "telemetry"; frame: unknown } | { type: "stream_closed" }) => void = () => {};
    const opener = vi.fn(async (_uuid: string, onMsg: typeof emit) => {
      emit = onMsg;
      return () => {};
    });
    render(<BurnLiveView uuid="b1" initial={snapshot()} live streamOpener={opener as never} />);
    expect(screen.getByText("LIVE")).toBeInTheDocument();
    expect(opener).toHaveBeenCalledWith("b1", expect.any(Function));
    emit({ type: "telemetry", frame: { channel: "T1", t_start: 3000, sample_period_s: 10, values: [500] } });
    await waitFor(() => {
      // new max reflected in the visible MAX badge (a visually-hidden
      // ChartFrame aria-describedby summary also mentions the peak value,
      // so scope to the badge's [data-gate] container specifically).
      const badge = document.querySelector("[data-gate]");
      expect(badge?.textContent).toContain("500.0");
    });
  });

  it("shows 'ended' when the stream closes", async () => {
    let emit: (m: { type: "stream_closed" }) => void = () => {};
    const opener = vi.fn(async (_u: string, onMsg: never) => {
      emit = onMsg as never;
      return () => {};
    });
    render(<BurnLiveView uuid="b1" initial={snapshot()} live streamOpener={opener as never} />);
    emit({ type: "stream_closed" });
    await waitFor(() => expect(screen.getByText(/Live view ended/i)).toBeInTheDocument());
  });

  it("degrades to static (no crash) when the stream opener rejects", async () => {
    const opener = vi.fn(async () => {
      throw new Error("SSE endpoint 404 — M2.4 not built yet");
    });
    render(<BurnLiveView uuid="b1" initial={snapshot()} live streamOpener={opener as never} />);
    await waitFor(() => expect(screen.getByText(/Live view ended/i)).toBeInTheDocument());
    // chart still rendered from the snapshot
    expect(document.querySelector("polyline")).not.toBeNull();
  });

  it("disposes the stream on unmount", async () => {
    const dispose = vi.fn();
    const opener = vi.fn(async () => dispose);
    const { unmount } = render(
      <BurnLiveView uuid="b1" initial={snapshot()} live streamOpener={opener as never} />,
    );
    await waitFor(() => expect(opener).toHaveBeenCalled());
    unmount();
    await waitFor(() => expect(dispose).toHaveBeenCalled());
  });

  it("synchronizes hover across both charts via the shared HoverSync context", () => {
    const { container } = render(<BurnLiveView uuid="b1" initial={snapshotWithLoad()} live={false} />);
    // Both charts render their hover-capture rect; the thermal chart's is first
    // in the DOM (ThermalMapChart renders before LoadTelemetryChart).
    const captureRects = container.querySelectorAll('rect[fill="transparent"]');
    expect(captureRects).toHaveLength(2);
    // jsdom's getBoundingClientRect returns a 0-width rect, so ChartFrame's
    // guard (`r.width > 0 ? ... : 0`) always yields frac=0 → hoverT = burn t_start
    // (1000). Both series have a sample exactly at t_start, so both tooltips
    // must appear showing that instant's values — proving the hover state is
    // SHARED (hovering the thermal chart also lights up the load tooltip).
    fireEvent.pointerMove(captureRects[0]);
    // Each chart renders its OWN tooltip label independently ("t+0:00" appears
    // twice — once per chart) but both must agree, proving one shared hoverT.
    expect(screen.getAllByText("t+0:00")).toHaveLength(2);
    expect(screen.getByText("400.0°C")).toBeInTheDocument();
    // "5 kg" also exists in LoadTelemetryChart's own <title> point-marker for
    // this same sample, so assert the tooltip's presence via its row text
    // instead of the ambiguous bare value.
    expect(screen.getByText("LOAD")).toBeInTheDocument();
    expect(screen.getAllByText("5 kg").length).toBeGreaterThanOrEqual(1);
    fireEvent.pointerLeave(captureRects[0]);
    expect(screen.queryByText("400.0°C")).toBeNull();
    expect(screen.queryByText("LOAD")).toBeNull();
  });
});
