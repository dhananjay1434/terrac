import { useState } from "react";
import type { MediaItem } from "../../api";
import { groupMedia, STEP_TITLES } from "../../pages/BatchDetail";
import EvidenceLightbox from "../EvidenceLightbox/EvidenceLightbox";
import MediaCell, { isVideo } from "../MediaCell/MediaCell";
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
              <MediaCell
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
