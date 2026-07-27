import { useEffect, useRef, useState } from "react";
import ThermalMapChart, { type ThermalMapData } from "../../ui/ThermalMapChart/ThermalMapChart";
import LoadTelemetryChart from "../../ui/LoadTelemetryChart/LoadTelemetryChart";
import { openBurnStream as realOpenBurnStream } from "../../api2";
import styles from "./BurnLiveView.module.css";

/**
 * Composes the thermal + load charts with the live SSE stream into one burn
 * view — the "watch a burn draw itself" experience. This is a COMPONENT, not a
 * page: the parent (BatchDetail, at the M2 stitch) fetches the initial snapshot
 * via api2.getTelemetry2 and passes it in; this component owns the real-time
 * append + stream lifecycle.
 *
 * Tier-aware (Global Rule 10): renders only channels that exist. Thermal-only
 * kiln → just the map; load-only → just the weight curve; zero channels →
 * returns null so BatchDetail falls back to the legacy TemperatureChart.
 * `live` opens the stream; when off (issued/historical batch) it's a static
 * view of the snapshot.
 */
export interface BurnLiveViewProps {
  uuid: string;
  initial: ThermalMapData;
  gateSatisfied?: boolean;
  live?: boolean;
  /** injectable for tests; defaults to the real api2 stream opener */
  streamOpener?: typeof realOpenBurnStream;
}

type Frame = { channel: string; t_start: string | number; sample_period_s: number; values: number[] };

function frameToPoints(f: Frame): [number, number][] {
  const t0 = typeof f.t_start === "number" ? f.t_start : Date.parse(f.t_start);
  const step = (f.sample_period_s || 10) * 1000;
  return f.values.map((v, i) => [t0 + i * step, v]);
}

function appendFrame(data: ThermalMapData, f: Frame): ThermalMapData {
  const pts = frameToPoints(f);
  if (!pts.length) return data;
  const existing = data.channels[f.channel];
  const merged = [...(existing?.points ?? []), ...pts];
  const values = merged.map((p) => p[1]);
  return {
    ...data,
    channels: {
      ...data.channels,
      [f.channel]: { points: merged, max: Math.max(...values), min: Math.min(...values) },
    },
    burn: {
      ...data.burn,
      t_end: Math.max(data.burn.t_end ?? 0, pts[pts.length - 1][0]),
    },
  };
}

export default function BurnLiveView({
  uuid,
  initial,
  gateSatisfied = false,
  live = false,
  streamOpener = realOpenBurnStream,
}: BurnLiveViewProps) {
  const [data, setData] = useState<ThermalMapData>(initial);
  const [status, setStatus] = useState<"live" | "ended" | "static">(live ? "live" : "static");
  const dataRef = useRef(data);
  dataRef.current = data;

  // keep in sync if the parent refetches a new snapshot
  useEffect(() => setData(initial), [initial]);

  useEffect(() => {
    if (!live) {
      setStatus("static");
      return;
    }
    setStatus("live");
    let dispose: (() => void) | null = null;
    let cancelled = false;
    streamOpener(uuid, (m) => {
      if (m.type === "telemetry") {
        setData((d) => appendFrame(d, m.frame as Frame));
      } else if (m.type === "stream_closed") {
        setStatus("ended");
      }
    }).then((d) => {
      if (cancelled) d();
      else dispose = d;
    });
    return () => {
      cancelled = true;
      dispose?.();
    };
  }, [uuid, live, streamOpener]);

  const hasThermal = ["T1", "T2", "T3", "T4"].some((c) => data.channels[c]?.points.length);
  const hasLoad = !!data.channels["LOAD"]?.points.length;
  if (!hasThermal && !hasLoad) return null; // tier-aware fallback

  const load = data.channels["LOAD"];

  return (
    <div className={styles.wrap}>
      {status !== "static" && (
        <div className={styles.statusRow} data-status={status}>
          <span className={styles.dot} aria-hidden />
          <span className="micro">{status === "live" ? "LIVE" : "Live view ended"}</span>
        </div>
      )}
      {hasThermal && <ThermalMapChart data={data} gateSatisfied={gateSatisfied} />}
      {hasLoad && <LoadTelemetryChart data={{ points: load.points }} />}
    </div>
  );
}

export { appendFrame }; // exported for unit test
