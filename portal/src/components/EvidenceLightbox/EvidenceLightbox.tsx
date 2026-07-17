import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { fetchMediaUrl, type MediaItem } from "../../api";
import CopyButton from "../CopyButton/CopyButton";
import styles from "./EvidenceLightbox.module.css";

/**
 * Full-screen evidence viewer (Radix Dialog: focus trap, Esc to close).
 * Shows the full media, complete SHA-256 in mono with copy, GPS, timestamp,
 * and the capture-type verification state. ←/→ navigate within the current
 * filter set. Controlled by the gallery via index/onClose/onNavigate.
 */
export default function EvidenceLightbox({
  items,
  index,
  onClose,
  onNavigate,
}: {
  items: MediaItem[];
  index: number | null;
  onClose(): void;
  onNavigate(next: number): void;
}) {
  const item = index !== null ? items[index] : null;
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    setUrl(null);
    if (!item) return;
    let live = true;
    let objUrl: string | null = null;
    fetchMediaUrl(item.operation_id)
      .then((u) => {
        objUrl = u;
        if (live) setUrl(u);
      })
      .catch(() => {});
    return () => {
      live = false;
      if (objUrl) URL.revokeObjectURL?.(objUrl);
    };
  }, [item?.operation_id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!item || index === null) return null;

  function onKeyDown(e: React.KeyboardEvent) {
    if (index === null) return;
    if (e.key === "ArrowRight" && index < items.length - 1)
      onNavigate(index + 1);
    if (e.key === "ArrowLeft" && index > 0) onNavigate(index - 1);
  }

  return (
    <Dialog.Root open onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.overlay} />
        <Dialog.Content
          className={styles.content}
          onKeyDown={onKeyDown}
          aria-describedby={undefined}
        >
          <Dialog.Title className={styles.title}>
            Evidence <span className="mono">{item.sha256_hash.slice(0, 12)}…</span>
          </Dialog.Title>
          <div className={styles.media}>
            {url ? (
              <img src={url} alt={item.filename ?? item.operation_id} />
            ) : (
              <span className={styles.unavailable}>media unavailable</span>
            )}
          </div>
          <dl className={styles.meta}>
            <div className={styles.row}>
              <dt>SHA-256</dt>
              <dd className="mono">
                {item.sha256_hash}{" "}
                <CopyButton value={item.sha256_hash} label="Copy SHA-256" />
              </dd>
            </div>
            <div className={styles.row}>
              <dt>Captured</dt>
              <dd className="tabular">
                {item.uploaded_at
                  ? item.uploaded_at.slice(0, 16).replace("T", " ")
                  : "—"}
              </dd>
            </div>
            <div className={styles.row}>
              <dt>GPS</dt>
              <dd>
                {item.exif_lat !== null && item.exif_lon !== null ? (
                  <>
                    <span className="tabular">
                      {item.exif_lat.toFixed(5)}, {item.exif_lon.toFixed(5)}
                    </span>{" "}
                    <CopyButton
                      value={`${item.exif_lat}, ${item.exif_lon}`}
                      label="Copy GPS"
                    />
                  </>
                ) : (
                  "no GPS"
                )}
              </dd>
            </div>
            <div className={styles.row}>
              <dt>Verification</dt>
              <dd>
                {item.capture_type_verified ? (
                  <span className="chip ok">✓ verified</span>
                ) : item.capture_type ? (
                  <span className="chip warn">unverified</span>
                ) : (
                  <span className="text-tertiary">unclassified</span>
                )}
              </dd>
            </div>
          </dl>
          <div className={styles.actions}>
            <button
              className="neutral"
              type="button"
              aria-label="Previous evidence"
              disabled={index === 0}
              onClick={() => onNavigate(index - 1)}
            >
              <ChevronLeft size={14} aria-hidden /> Prev
            </button>
            <span className="micro tabular">
              {index + 1} / {items.length}
            </span>
            <button
              className="neutral"
              type="button"
              aria-label="Next evidence"
              disabled={index === items.length - 1}
              onClick={() => onNavigate(index + 1)}
            >
              Next <ChevronRight size={14} aria-hidden />
            </button>
            <Dialog.Close asChild>
              <button className="primary" type="button">
                Close
              </button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
