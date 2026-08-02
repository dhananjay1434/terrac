import { useState, type ReactNode } from "react";
import { Maximize2 } from "lucide-react";
import ChartExpandModal from "../ChartExpandModal/ChartExpandModal";
import styles from "./TelemetryCard.module.css";

/** A compact, modular telemetry chart card. The WHOLE card is the expand
 * control (click or Enter/Space) — same "small → open → act inside" idiom as
 * EvidenceGallery→EvidenceLightbox (blueprint audit F1). Actions (download)
 * live in the modal footer, not on the card. */
export default function TelemetryCard({
  title,
  children,
  expandedChildren,
  actions,
}: {
  title: string;
  /** compact inline chart */
  children: ReactNode;
  /** the same chart at a large height for the modal */
  expandedChildren: ReactNode;
  /** modal footer actions (e.g. Download CSV) */
  actions?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <div
        className={styles.card}
        role="button"
        tabIndex={0}
        aria-label={`Expand ${title}`}
        onClick={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen(true);
          }
        }}
      >
        {/* No visible title here — the chart itself (ChartFrame) already
            renders `title` in its own header; repeating it would duplicate
            the heading. The glyph is purely a hover/focus affordance; the
            accessible name lives on the card's aria-label. */}
        <Maximize2 size={14} className={styles.glyph} aria-hidden />
        {children}
      </div>
      <ChartExpandModal open={open} onClose={() => setOpen(false)} title={title} actions={actions}>
        {expandedChildren}
      </ChartExpandModal>
    </>
  );
}
