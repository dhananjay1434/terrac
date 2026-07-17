import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import clsx from "clsx";
import CopyButton from "../CopyButton/CopyButton";
import styles from "./ConfirmModal.module.css";

export interface PreviewRow {
  label: string;
  value: string;
  mono?: boolean;
}

/**
 * High-stakes confirmation dialog: preview block, amber warning, and a typed
 * dynamic token that must match exactly before the confirm button enables.
 * All inputs disable while onConfirm is pending. Radix Dialog provides the
 * focus trap, Esc-close, and focus return.
 */
export default function ConfirmModal({
  open,
  onOpenChange,
  title,
  previewRows,
  warning,
  confirmToken,
  confirmLabel,
  danger = false,
  onConfirm,
}: {
  open: boolean;
  onOpenChange(open: boolean): void;
  title: string;
  previewRows: PreviewRow[];
  warning?: string;
  confirmToken: string;
  confirmLabel: string;
  danger?: boolean;
  onConfirm(): Promise<void>;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) setText("");
  }, [open]);

  async function confirm() {
    setBusy(true);
    try {
      await onConfirm();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !busy && onOpenChange(o)}>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.overlay} />
        <Dialog.Content className={styles.content} aria-describedby={undefined}>
          <Dialog.Title className={styles.title}>{title}</Dialog.Title>
          <dl className={styles.preview}>
            {previewRows.map((r) => (
              <div key={r.label} className={styles.row}>
                <dt>{r.label}</dt>
                <dd className={r.mono ? "mono tabular" : undefined}>
                  {r.value}
                </dd>
              </div>
            ))}
          </dl>
          {warning && <div className={styles.warning}>{warning}</div>}
          <label className="micro" htmlFor="confirm-token">
            Type{" "}
            <span className="mono">{confirmToken}</span>{" "}
            <CopyButton value={confirmToken} label="Copy confirmation token" />
            {" "}to confirm
          </label>
          <input
            id="confirm-token"
            className={styles.input}
            value={text}
            disabled={busy}
            autoComplete="off"
            spellCheck={false}
            aria-invalid={text.length > 0 && text.trim() !== confirmToken}
            aria-describedby={
              text.length > 0 ? "confirm-token-feedback" : undefined
            }
            onChange={(e) => setText(e.target.value)}
          />
          <div id="confirm-token-feedback" className={styles.feedback}>
            {text.length > 0 &&
              (text.trim() === confirmToken ? (
                <span className={styles.match}>✓ Matches</span>
              ) : (
                <span className={styles.mismatch}>
                  Doesn't match — type it exactly
                </span>
              ))}
          </div>
          <div className={styles.actions}>
            <Dialog.Close asChild>
              <button className="neutral" type="button" disabled={busy}>
                Cancel
              </button>
            </Dialog.Close>
            <button
              type="button"
              className={clsx(styles.confirm, danger && styles.danger)}
              disabled={text.trim() !== confirmToken || busy}
              onClick={confirm}
            >
              {busy ? "Working…" : confirmLabel}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
