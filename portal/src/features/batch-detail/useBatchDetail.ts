import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getBatch,
  getBatchTimeline,
  issueCredit,
  downloadExport,
  AuthError,
  ApiError,
  type BatchDetail as Detail,
  type MediaItem,
  type TimelineStage,
} from "../../api";
import { getBatchCapabilities } from "../../api2";
import type { BatchCapabilities } from "../../apiV2types";
import { fmtDate } from "../../format";

const TIMELINE_V2 = true; // M3.3 feature flag

/**
 * Owns all BatchDetail page data: the batch record, capability probe, custody
 * timeline, issue/export actions, and the derived verification-chain nodes.
 * The page composes this state into JSX; it fetches and transforms nothing
 * itself.
 */
export function useBatchDetail(uuid: string) {
  const nav = useNavigate();
  const [d, setD] = useState<Detail | null>(null);
  const [timeline, setTimeline] = useState<TimelineStage[]>([]);
  const [caps, setCaps] = useState<BatchCapabilities | null>(null);
  const [timelineLightbox, setTimelineLightbox] = useState<MediaItem | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [issuing, setIssuing] = useState(false);
  const [exporting, setExporting] = useState<"csi" | "rainbow" | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  function reload() {
    setErr(null);
    getBatch(uuid)
      .then(setD)
      .catch((e) => {
        if (e instanceof AuthError) nav("/login");
        else if (e instanceof ApiError && e.status === 404)
          setErr("Batch not found.");
        else setErr("Couldn't load batch.");
      });

    getBatchCapabilities(uuid)
      .then(setCaps)
      .catch(() => {
        // Best-effort probe: on failure we fall back to the pre-capability default
        // (show panels) so a failed probe never blanks a batch that has data.
      });

    if (TIMELINE_V2) {
      getBatchTimeline(uuid)
        .then(setTimeline)
        .catch((e) => {
          // If legacy batch (404 timeline), no crash, just gallery
          if (e instanceof ApiError && e.status === 404) return;
          console.error("Failed to load timeline", e);
        });
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uuid]);

  useEffect(() => {
    if (d) document.title = `Batch ${uuid.slice(0, 8)} · TerraCipher`;
  }, [d, uuid]);

  async function issue() {
    if (!d) return;
    setIssuing(true);
    try {
      await issueCredit(uuid);
      setConfirmOpen(false);
      reload();
    } catch (e) {
      if (e instanceof AuthError) nav("/login");
      else setErr("Issue failed — the server re-checks eligibility.");
    } finally {
      setIssuing(false);
    }
  }

  async function exportAs(fmt: "csi" | "rainbow") {
    if (!d) return;
    setExporting(fmt);
    try {
      await downloadExport(uuid, fmt);
    } catch (e) {
      if (e instanceof AuthError) nav("/login");
      else setErr("Export failed — the batch must be issuable to export.");
    } finally {
      setExporting(null);
    }
  }

  // Render from the server's stated verdict; if caps haven't loaded or the probe
  // failed, fall back to TIMELINE_V2 (today's behavior) so nothing regresses.
  const showTimeline = caps?.timeline ?? TIMELINE_V2;
  const showThermal = caps ? caps.thermal : true;
  const showLoad = caps ? caps.load : false;

  const chainNodes = d
    ? (() => {
        const okCount = d.compliance.checklist.filter((c) => c.ok).length;
        const total = d.compliance.checklist.length;
        const issued = d.batch.status === "ISSUED";
        return [
          {
            label: "Received",
            sublabel: d.batch.received_at ? fmtDate(d.batch.received_at) : undefined,
            state: d.batch.received_at ? ("done" as const) : ("pending" as const),
          },
          {
            label: "Evidence",
            sublabel: `${d.media.length} item${d.media.length === 1 ? "" : "s"}`,
            state: d.media.length > 0 ? ("done" as const) : ("pending" as const),
          },
          {
            label: "Compliance",
            sublabel: `${okCount}/${total} criteria`,
            state: d.compliance.issuable ? ("done" as const) : ("current" as const),
          },
          {
            label: "Issued",
            state: issued ? ("done" as const) : ("pending" as const),
          },
        ];
      })()
    : [];

  return {
    d,
    timeline,
    timelineLightbox,
    setTimelineLightbox,
    err,
    issuing,
    exporting,
    confirmOpen,
    setConfirmOpen,
    reload,
    issue,
    exportAs,
    showTimeline,
    showThermal,
    showLoad,
    chainNodes,
  };
}
