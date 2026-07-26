import { useEffect, useState } from "react";
import { ImageOff } from "lucide-react";
import { fetchMediaUrl, verifyMedia, type MediaItem } from "../../api";
import { getRole } from "../../auth";
// Canonical grouping + titles live in BatchDetail (with passing tests) — read,
// never redefined. The import cycle is safe: only referenced at render time.
import { groupMedia, STEP_TITLES } from "../../pages/BatchDetail";
import CopyButton from "../CopyButton/CopyButton";
import Skeleton from "../Skeleton/Skeleton";
import EvidenceLightbox from "../EvidenceLightbox/EvidenceLightbox";
import { fmtDateTime } from "../../format";
import StatusPill from "../../ui/StatusPill/StatusPill";
import styles from "./EvidenceGallery.module.css";

type Filter = "all" | "photos" | "videos" | "certificates";
const FILTER_LABEL: Record<Filter, string> = {
  all: "All",
  photos: "Photos",
  videos: "Videos",
  certificates: "Certificates",
};

function isCertificate(m: MediaItem) {
  return (
    m.capture_type === "lab_certificate" || /\.pdf$/i.test(m.filename ?? "")
  );
}
export function isVideo(m: { capture_type?: string | null; filename?: string | null }) {
  return (
    /\.(mp4|mov|webm)$/i.test(m.filename ?? "") ||
    !!m.capture_type?.endsWith("_video")
  );
}
function matches(filter: Filter, m: MediaItem) {
  if (filter === "all") return true;
  if (filter === "certificates") return isCertificate(m);
  if (filter === "videos") return isVideo(m);
  return !isCertificate(m) && !isVideo(m);
}

function titleOf(stage: string) {
  return stage === "__unclassified__"
    ? STEP_TITLES["other"]
    : (STEP_TITLES[stage] ?? stage);
}

/** V8 Part 4 (K) — reviewer verdict controls, visible only to verifier/admin
 * roles. Two-step reject (reveal a reason field) keeps the reason mandatory
 * without a native `window.prompt` (untestable, poor a11y). */
function VerdictControls({
  item,
  locked = false,
  onVerified,
}: {
  item: MediaItem;
  locked?: boolean;
  onVerified(status: string, remarks: string | null): void;
}) {
  const role = getRole();
  const [rejecting, setRejecting] = useState(false);
  const [overriding, setOverriding] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  if (role !== "verifier" && role !== "admin") return null;
  // Once the batch is issued its evidence verdicts are frozen — no controls.
  if (locked) return null;

  async function approve() {
    setBusy(true);
    setErr(null);
    try {
      const res = await verifyMedia(item.operation_id, { status: "approved" });
      onVerified(res.verification_status ?? "approved", res.verification_remarks);
      setOverriding(false);
    } catch {
      setErr("Save failed — retry");
    } finally {
      setBusy(false);
    }
  }

  async function confirmReject() {
    setBusy(true);
    setErr(null);
    try {
      const res = await verifyMedia(item.operation_id, {
        status: "rejected",
        remarks: reason.trim() || undefined,
      });
      onVerified(res.verification_status ?? "rejected", res.verification_remarks);
      setRejecting(false);
      setReason("");
      setOverriding(false);
    } catch {
      setErr("Save failed — retry");
    } finally {
      setBusy(false);
    }
  }

  // Already reviewed and not currently changing it → collapse to a single
  // "Change verdict" affordance so the decision reads as settled.
  if (item.verification_status && !overriding && !rejecting) {
    return (
      <div className={styles.verdictRow}>
        <button
          type="button"
          className="linkbtn"
          onClick={() => setOverriding(true)}
        >
          Change verdict
        </button>
        {err && <StatusPill status="error">{err}</StatusPill>}
      </div>
    );
  }

  if (rejecting) {
    return (
      <div className={styles.verdictRow} style={{ flexDirection: "column" }}>
        <input
          aria-label={`Rejection reason for ${item.operation_id}`}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Reason for rejection"
        />
        <div className={styles.verdictRow}>
          <button
            type="button"
            className={styles.verdictBtn}
            disabled={busy}
            onClick={confirmReject}
          >
            Confirm reject
          </button>
          <button
            type="button"
            className={styles.verdictBtn}
            onClick={() => setRejecting(false)}
          >
            Cancel
          </button>
        </div>
        {err && <StatusPill status="error">{err}</StatusPill>}
      </div>
    );
  }

  return (
    <div className={styles.verdictRow}>
      <button
        type="button"
        className={styles.verdictBtn}
        disabled={busy}
        onClick={approve}
      >
        Approve
      </button>
      <button
        type="button"
        className={styles.verdictBtn}
        disabled={busy}
        onClick={() => setRejecting(true)}
      >
        Reject
      </button>
      {err && <StatusPill status="error">{err}</StatusPill>}
    </div>
  );
}

function GalleryThumb({
  item,
  locked,
  onOpen,
  onVerified,
}: {
  item: MediaItem;
  locked?: boolean;
  onOpen(): void;
  onVerified(status: string, remarks: string | null): void;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let live = true;
    let objUrl: string | null = null;
    fetchMediaUrl(item.operation_id)
      .then((u) => {
        objUrl = u;
        if (live) setUrl(u);
      })
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
      if (objUrl) URL.revokeObjectURL?.(objUrl);
    };
  }, [item.operation_id]);
  return (
    <div className="media-cell">
      <button
        type="button"
        className={`${styles.thumbBtn} thumb-print-keep`}
        onClick={onOpen}
        aria-label={`Open evidence ${item.sha256_hash.slice(0, 12)}`}
      >
        {url ? (
          isVideo(item) ? (
            <video
              src={url}
              muted
              playsInline
              preload="metadata"
              className={loaded ? styles.loaded : undefined}
              onLoadedData={() => setLoaded(true)}
            />
          ) : (
            <img
              src={url}
              alt={item.filename ?? item.operation_id}
              className={loaded ? styles.loaded : undefined}
              onLoad={() => setLoaded(true)}
            />
          )
        ) : failed ? (
          <span className={styles.fallback}>
            <ImageOff size={16} aria-hidden />
            <span className={styles.fallbackLabel}>Preview unavailable</span>
          </span>
        ) : (
          <span className={styles.loading}>
            <Skeleton variant="row" />
          </span>
        )}
      </button>
      <div className="forensic-meta">
        <div className={styles.hashRow}>
          <span className="mono">{item.sha256_hash.slice(0, 12)}…</span>
          <CopyButton value={item.sha256_hash} label="Copy SHA-256" />
        </div>
        <div className={styles.metaLine}>
          {fmtDateTime(item.uploaded_at)}
        </div>
        <div className={styles.metaLine}>
          {item.exif_lat !== null && item.exif_lon !== null ? (
            <a
              className={styles.gpsLink}
              href={`https://www.openstreetmap.org/?mlat=${item.exif_lat}&mlon=${item.exif_lon}#map=17/${item.exif_lat}/${item.exif_lon}`}
              target="_blank"
              rel="noreferrer"
            >
              {item.exif_lat.toFixed(5)}, {item.exif_lon.toFixed(5)}
            </a>
          ) : (
            "—"
          )}
        </div>
        <div className={styles.chipRow}>
          {item.capture_type_verified ? (
            <StatusPill status="success">Type verified</StatusPill>
          ) : item.capture_type ? (
            <StatusPill status="warning">Type unverified</StatusPill>
          ) : null}
          {item.verification_status === "approved" && (
            <StatusPill status="success">Review approved</StatusPill>
          )}
          {item.verification_status === "rejected" && (
            <StatusPill status="error">Review rejected</StatusPill>
          )}
        </div>
        {item.verification_status === "rejected" && item.verification_remarks && (
          <div className={styles.remarks}>{item.verification_remarks}</div>
        )}
        <VerdictControls item={item} locked={locked} onVerified={onVerified} />
      </div>
    </div>
  );
}

/**
 * Case-file evidence gallery: numbered chapters per capture step (order from
 * STEP_ORDER via groupMedia), client-side filter tabs, forensic metadata per
 * cell, and a lightbox on click. Dead thumbnails keep their metadata visible.
 */
export default function EvidenceGallery({
  media,
  locked = false,
}: {
  media: MediaItem[];
  locked?: boolean;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const [lightbox, setLightbox] = useState<number | null>(null);
  // Local verdict overrides so Approve/Reject reflect immediately without
  // requiring the parent to refetch the whole batch detail.
  const [overrides, setOverrides] = useState<
    Record<string, { status: string; remarks: string | null }>
  >({});

  if (media.length === 0) return null;
  const withOverrides = media.map((m) =>
    overrides[m.operation_id]
      ? {
          ...m,
          verification_status: overrides[m.operation_id].status,
          verification_remarks: overrides[m.operation_id].remarks,
        }
      : m,
  );
  const filtered = withOverrides.filter((m) => matches(filter, m));
  const groups = groupMedia(filtered);

  return (
    <section className="card" style={{ marginTop: "var(--space-4)" }} id="evidence-media">
      <div className={styles.head}>
        <span className="micro">Evidence media</span>
        <div role="tablist" aria-label="Evidence filter" className={styles.tabs}>
          {(Object.keys(FILTER_LABEL) as Filter[]).map((f) => (
            <button
              key={f}
              role="tab"
              type="button"
              aria-selected={filter === f}
              className={`linkbtn ${filter === f ? "active" : ""}`}
              onClick={() => setFilter(f)}
            >
              {FILTER_LABEL[f]}
            </button>
          ))}
        </div>
      </div>
      {groups.map(([stage, items], gi) => (
        <div key={stage} className="evidence-group" id={`evidence-${stage}`}>
          <div className="evidence-group-head">
            <h3>
              {gi + 1}. {titleOf(stage)} · {items.length} item
              {items.length === 1 ? "" : "s"}
            </h3>
          </div>
          <div className="media-grid">
            {items.map((m) => (
              <GalleryThumb
                key={m.sha256_hash}
                item={m}
                locked={locked}
                onOpen={() => setLightbox(filtered.indexOf(m))}
                onVerified={(status, remarks) =>
                  setOverrides((o) => ({
                    ...o,
                    [m.operation_id]: { status, remarks },
                  }))
                }
              />
            ))}
          </div>
        </div>
      ))}
      <EvidenceLightbox
        items={filtered}
        index={lightbox}
        onClose={() => setLightbox(null)}
        onNavigate={setLightbox}
      />
    </section>
  );
}
