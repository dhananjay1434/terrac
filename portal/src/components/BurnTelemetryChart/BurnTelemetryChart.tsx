import { useEffect, useState } from "react";
import TemperatureChart from "../TemperatureChart/TemperatureChart";
import BurnLiveView from "../BurnLiveView/BurnLiveView";
import { getTelemetry2, type TelemetryResponse } from "../../api2";

/**
 * The M2 chart stitch, done graceful-degradation style (Global Rule 10). Tries
 * the v2 telemetry read (api2.getTelemetry2); if real channels come back it
 * renders the live BurnLiveView, otherwise it falls back to the legacy
 * app-evidence TemperatureChart — exactly today's behavior.
 *
 * This means the wiring is CORRECT before the M2.3 read endpoint exists (the
 * fetch 404s → fallback) and lights up automatically the moment M2.3 ships,
 * with zero further edits to BatchDetail. `live` opens the SSE stream when the
 * batch is still in progress (BurnLiveView degrades to static if M2.4 is absent).
 */
export default function BurnTelemetryChart({
  uuid,
  legacyReadings,
  legacyMin,
  legacyMax,
  gateSatisfied = false,
  live = false,
}: {
  uuid: string;
  legacyReadings: number[];
  legacyMin: number | null;
  legacyMax: number | null;
  gateSatisfied?: boolean;
  live?: boolean;
}) {
  const [v2, setV2] = useState<TelemetryResponse | null>(null);

  useEffect(() => {
    let live_ = true;
    getTelemetry2(uuid)
      .then((res) => {
        // only adopt v2 when it actually carries channel data (tier-aware)
        const hasData = Object.values(res.channels ?? {}).some((c) => c?.points?.length);
        if (live_ && hasData) setV2(res);
      })
      .catch(() => {
        /* endpoint absent (pre-M2.3) or no telemetry → keep legacy fallback */
      });
    return () => {
      live_ = false;
    };
  }, [uuid]);

  if (v2) {
    return (
      <BurnLiveView
        uuid={uuid}
        initial={{ channels: v2.channels, burn: v2.burn }}
        gateSatisfied={gateSatisfied}
        live={live}
      />
    );
  }
  return (
    <TemperatureChart readings={legacyReadings} minTemp={legacyMin} maxTemp={legacyMax} />
  );
}
