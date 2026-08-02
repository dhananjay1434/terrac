import type { ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import Button from "../Button/Button";
import styles from "./ChartExpandModal.module.css";

/**
 * Generic large-view modal for a telemetry chart. Modeled EXACTLY on
 * EvidenceLightbox (Radix Dialog: focus trap, Esc to close) so "click a small
 * thing → see it big → act inside it" is ONE idiom across the whole portal,
 * not a second competing one for charts (blueprint audit F1).
 */
export default function ChartExpandModal({
  open,
  onClose,
  title,
  actions,
  children,
}: {
  open: boolean;
  onClose(): void;
  title: string;
  /** Footer action buttons (e.g. Download CSV/PNG). */
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.overlay} />
        <Dialog.Content className={styles.content} aria-describedby={undefined}>
          <Dialog.Title className={styles.title}>{title}</Dialog.Title>
          <div className={styles.body}>{children}</div>
          <div className={styles.actions}>
            {actions}
            <Dialog.Close asChild>
              <Button variant="neutral">Close</Button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
