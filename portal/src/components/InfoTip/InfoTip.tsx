import * as Tooltip from "@radix-ui/react-tooltip";
import { Info } from "lucide-react";
import styles from "./InfoTip.module.css";

/**
 * Small "?" info trigger for jargon terms. Requires a Tooltip.Provider
 * ancestor (AppShell supplies one for authed screens).
 */
export default function InfoTip({ label }: { label: string }) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <button
          type="button"
          className={styles.trigger}
          aria-label={`Help: ${label}`}
        >
          <Info size={12} aria-hidden />
        </button>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content className={styles.content} sideOffset={4}>
          {label}
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
