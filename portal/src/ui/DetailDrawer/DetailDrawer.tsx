import type { ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import styles from "./DetailDrawer.module.css";

/**
 * Right-side slide-in detail panel — the generalized `JourneyPanel` shell.
 * Built on Radix Dialog so focus-trap, ESC-close, scrim-click-close, and
 * focus-return-to-trigger all come for free instead of being reimplemented.
 * Full-width sheet below 768px (see DetailDrawer.module.css).
 */
export default function DetailDrawer({
  open,
  onOpenChange,
  title,
  children,
}: {
  open: boolean;
  onOpenChange(open: boolean): void;
  title: string;
  children: ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.overlay} />
        <Dialog.Content className={styles.panel} aria-describedby={undefined}>
          <div className={styles.head}>
            <Dialog.Title className={styles.title}>{title}</Dialog.Title>
            <Dialog.Close asChild>
              <button type="button" className={styles.close} aria-label="Close">
                <X size={16} aria-hidden />
              </button>
            </Dialog.Close>
          </div>
          <div className={styles.body}>{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
