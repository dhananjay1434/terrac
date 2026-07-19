import { useEffect, useState } from "react";
import { fetchMediaUrl, type MediaItem } from "../../api";
// Canonical grouping + titles live in BatchDetail (with passing tests) — read,
// never redefined. The import cycle is safe: only referenced at render time.
import { groupMedia, STEP_TITLES } from "../../pages/BatchDetail";
import CopyButton from "../CopyButton/CopyButton";
import Skeleton from "../Skeleton/Skeleton";
import EvidenceLightbox from "../EvidenceLightbox/EvidenceLightbox";
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
function isVideo(m: MediaItem) {
  return /\.(mp4|mov|webm)$/i.test(m.filename ?? "");
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

function GalleryThumb({
  item,
  onOpen,
}: {
  item: MediaItem;
  onOpen(): void;
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
        className={styles.thumbBtn}
        onClick={onOpen}
        aria-label={`Open evidence ${item.sha256_hash.slice(0, 12)}`}
      >
        {url ? (
          <img
            src={url}
            alt={item.filename ?? item.operation_id}
            className={loaded ? styles.loaded : undefined}
            onLoad={() => setLoaded(true)}
          />
        ) : failed ? (
          <span className={styles.fallback}>
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden
            >
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
              <line x1="1" y1="1" x2="23" y2="23"></line>
            </svg>
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
          {item.uploaded_at
            ? item.uploaded_at.slice(0, 16).replace("T", " ")
            : "—"}
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
            "no GPS"
          )}
        </div>
        <div className={styles.chipRow}>
          {item.capture_type_verified ? (
            <span className="chip ok">✓ verified</span>
          ) : item.capture_type ? (
            <span className="chip warn">unverified</span>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/**
 * Case-file evidence gallery: numbered chapters per capture step (order from
 * STEP_ORDER via groupMedia), client-side filter tabs, forensic metadata per
 * cell, and a lightbox on click. Dead thumbnails keep their metadata visible.
 */
export default function EvidenceGallery({ media }: { media: MediaItem[] }) {
  const [filter, setFilter] = useState<Filter>("all");
  const [lightbox, setLightbox] = useState<number | null>(null);

  if (media.length === 0) return null;
  const filtered = media.filter((m) => matches(filter, m));
  const groups = groupMedia(filtered);

  return (
    <section className="card" style={{ marginTop: 14 }} id="evidence-media">
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
                onOpen={() => setLightbox(filtered.indexOf(m))}
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
