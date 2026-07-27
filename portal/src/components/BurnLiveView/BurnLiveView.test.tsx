import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import BurnLiveView, { appendFrame } from "./BurnLiveView";
import type { ThermalMapData } from "../../ui/ThermalMapChart/ThermalMapChart";

function snapshot(): ThermalMapData {
  return {
    channels: { T1: { points: [[1000, 400]], max: 400, min: 400 } },
    burn: { t_start: 1000, t_end: 1000 },
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
      // new max reflected in the MAX badge
      expect(screen.getByText(/500.0/)).toBeInTheDocument();
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
});
