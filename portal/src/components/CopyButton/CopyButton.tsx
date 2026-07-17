import { useState } from "react";
import { Copy, Check } from "lucide-react";

/**
 * Ghost copy-to-clipboard button. Swaps to a check icon briefly after a
 * successful copy, and announces success via an aria-live region — the icon
 * swap alone is invisible to screen-reader users. Clipboard writes are
 * always user-initiated.
 */
export default function CopyButton({
  value,
  label = "Copy",
}: {
  value: string;
  label?: string;
}) {
  const [copied, setCopied] = useState(false);
  return (
    <>
      <button
        type="button"
        className="linkbtn"
        aria-label={label}
        onClick={(e) => {
          e.stopPropagation();
          navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }}
      >
        {copied ? <Check size={12} aria-hidden /> : <Copy size={12} aria-hidden />}
      </button>
      <span
        role="status"
        aria-live="polite"
        style={{
          position: "absolute",
          width: 1,
          height: 1,
          overflow: "hidden",
          clip: "rect(0 0 0 0)",
        }}
      >
        {copied ? "Copied" : ""}
      </span>
    </>
  );
}
