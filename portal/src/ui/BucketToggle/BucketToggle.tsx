import { useRef } from "react";
import styles from "./BucketToggle.module.css";

export interface BucketToggleProps {
  selected: "month" | "day";
  onSelect: (bucket: "month" | "day") => void;
}

/** Segmented control for toggling between month and day bucket views.
 * Simple two-button pattern with keyboard navigation support (arrow keys). */
export default function BucketToggle({ selected, onSelect }: BucketToggleProps) {
  const monthBtnRef = useRef<HTMLButtonElement>(null);
  const dayBtnRef = useRef<HTMLButtonElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      const otherOption = selected === "month" ? "day" : "month";
      const otherRef = selected === "month" ? dayBtnRef : monthBtnRef;
      otherRef.current?.focus();
      onSelect(otherOption);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      const otherOption = selected === "month" ? "day" : "month";
      const otherRef = selected === "month" ? dayBtnRef : monthBtnRef;
      otherRef.current?.focus();
      onSelect(otherOption);
    }
  };

  return (
    <div className={styles.toggle}>
      <button
        ref={monthBtnRef}
        className={styles.option}
        data-selected={selected === "month"}
        aria-selected={selected === "month"}
        aria-pressed={selected === "month"}
        onClick={() => onSelect("month")}
        onKeyDown={handleKeyDown}
      >
        Month
      </button>
      <button
        ref={dayBtnRef}
        className={styles.option}
        data-selected={selected === "day"}
        aria-selected={selected === "day"}
        aria-pressed={selected === "day"}
        onClick={() => onSelect("day")}
        onKeyDown={handleKeyDown}
      >
        Day
      </button>
    </div>
  );
}
