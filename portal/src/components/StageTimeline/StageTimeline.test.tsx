import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import type { TimelineStage } from "../../api";
import StageTimeline from "./StageTimeline";

const base: TimelineStage[] = [
  {
    stage: "firing",
    started_at: "2026-07-22T13:02:00Z",
    ended_at: "2026-07-22T15:02:00Z",
    state: "done",
    media: [{ operation_id: "op1", sha256_hash: "abc", exif_lat: null, exif_lon: null } as any],
    telemetry_summary: { max_temp: 477, duration_min: 120 },
  },
  {
    stage: "mixing",
    started_at: null,
    ended_at: null,
    state: "empty",
    blocking: true,
  },
];

describe("StageTimeline", () => {
  it("renders a node per stage with humanized titles", () => {
    const { getByText } = render(<StageTimeline stages={base} />);
    expect(getByText("Firing")).toBeInTheDocument();
    expect(getByText("Mixing")).toBeInTheDocument();
  });

  it("shows telemetry summary on a done stage", () => {
    const { getByText } = render(<StageTimeline stages={base} />);
    expect(getByText(/max 477°C · 120 min/)).toBeInTheDocument();
  });

  it("shows an explicit empty state (absence is visible)", () => {
    const { getByText } = render(<StageTimeline stages={base} />);
    expect(getByText(/no mixing records/i)).toBeInTheDocument();
  });

  it("flags a blocking empty stage with a warning pill", () => {
    const { getByText } = render(<StageTimeline stages={base} />);
    expect(getByText(/blocking issuance/i)).toBeInTheDocument();
  });

  it("renders nothing for an empty timeline (legacy batch fallback)", () => {
    const { container } = render(<StageTimeline stages={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("humanizes an unknown stage without crashing", () => {
    const { getAllByText } = render(
      <StageTimeline
        stages={[{ stage: "some_new_stage", started_at: null, ended_at: null, state: "empty" }]}
      />,
    );
    // appears in both the title and the empty-state line — both are correct
    expect(getAllByText(/some new stage/i).length).toBeGreaterThan(0);
  });
});
