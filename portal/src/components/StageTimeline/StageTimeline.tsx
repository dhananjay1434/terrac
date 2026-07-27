import { fmtDateTime } from "../../format";
import type { MediaItem, TimelineStage } from "../../api";
import StatusPill from "../../ui/StatusPill/StatusPill";
import MediaCell from "../MediaCell/MediaCell";
import styles from "./StageTimeline.module.css";

/**
 * Vertical custody-chain timeline (M3.3). Consumes the M3.2 timeline endpoint
 * shape and renders each stage on a spine (VerificationChain visual language:
 * markers + connectors from tokens). Empty stages ARE shown ("no records") so
 * absence is visible; a stage that is empty AND blocks issuance carries a
 * "blocking" pill — the WHY-it-matters signal a plain timeline lacks.
 *
 * Self-contained by design (no EvidenceGallery import) so it ships from the
 * parallel lane without touching shared components; the media chip can be
 * upgraded to gallery thumbnails at the M3 stitch.
 */

const STAGE_TITLES: Record<string, string> = {
  sourcing: "Sourcing",
  moisture: "Moisture",
  loading: "Loading",
  firing: "Firing",
  biochar_addition: "Biochar addition",
  pre_quenching: "Pre-quenching",
  quenching: "Quenching",
  yield: "Yield",
  mixing: "Mixing",
  packaging: "Packaging",
  dispatch: "Dispatch",
  application: "Application",
  lab: "Lab",
};

function title(stage: string): string {
  return STAGE_TITLES[stage] ?? stage.replace(/_/g, " ");
}

function marker(state: TimelineStage["state"], blocking?: boolean): string {
  if (state === "done") return "✓";
  if (state === "active") return "●";
  return blocking ? "!" : "—";
}

export default function StageTimeline({
  stages,
  locked,
  onOpenMedia,
  onVerified,
}: {
  stages: TimelineStage[];
  locked?: boolean;
  onOpenMedia?: (item: MediaItem) => void;
  onVerified?: (opId: string, status: string, remarks: string | null) => void;
}) {
  if (!stages.length) return null;
  return (
    <ol className={styles.timeline} aria-label="Batch custody timeline">
      {stages.map((s, i) => {
        const count = s.media?.length ?? 0;
        return (
          <li
            key={s.stage}
            className={styles.node}
            data-state={s.state}
            data-blocking={s.blocking ? "true" : undefined}
          >
            <span className={styles.marker} aria-hidden>
              {marker(s.state, s.blocking)}
            </span>
            {i < stages.length - 1 && <span className={styles.connector} aria-hidden />}
            <div className={styles.body}>
              <div className={styles.head}>
                <span className={styles.title}>{title(s.stage)}</span>
                {s.started_at && (
                  <span className={`${styles.time} mono`}>
                    {fmtDateTime(s.started_at)}
                    {s.ended_at ? ` → ${fmtDateTime(s.ended_at)}` : ""}
                  </span>
                )}
              </div>
              {s.state === "empty" ? (
                <div className={styles.empty}>
                  <span className="text-tertiary">— no {title(s.stage).toLowerCase()} records</span>
                  {s.blocking && <StatusPill status="warning">blocking issuance</StatusPill>}
                </div>
              ) : (
                <div className={styles.meta}>
                  {s.telemetry_summary && (
                    <span className={`${styles.chip} mono tabular`} style={{ marginBottom: "var(--space-2)" }}>
                      max {s.telemetry_summary.max_temp}°C · {s.telemetry_summary.duration_min} min
                    </span>
                  )}
                  {count > 0 && s.media && (
                    <div className="media-grid">
                      {s.media.map((m) => (
                        <MediaCell
                          key={m.sha256_hash}
                          item={m}
                          locked={locked}
                          onOpen={() => onOpenMedia?.(m)}
                          onVerified={onVerified ? (status, remarks) => onVerified(m.operation_id, status, remarks) : undefined}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
