import { useRef } from "react";
import styles from "./BucketToggle.module.css";

export interface BucketToggleOption<V extends string = string> {
  value: V;
  label: string;
}

export interface BucketToggleProps<V extends string = string> {
  options: BucketToggleOption<V>[];
  selected: V;
  onSelect: (value: V) => void;
  /** Accessible group label (e.g. "Chart granularity"). */
  ariaLabel?: string;
}

/**
 * Generic segmented control — a horizontal row of mutually-exclusive options.
 * Options are caller-supplied (never hardcoded here), so the same control
 * drives 2-way or N-way choices. Roving-focus arrow-key navigation, and
 * selecting an option moves focus to it (standard segmented-control a11y).
 */
export default function BucketToggle<V extends string = string>({
  options,
  selected,
  onSelect,
  ariaLabel,
}: BucketToggleProps<V>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const move = (from: number, delta: number) => {
    const next = (from + delta + options.length) % options.length;
    refs.current[next]?.focus();
    onSelect(options[next].value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, i: number) => {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      move(i, 1);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      move(i, -1);
    }
  };

  return (
    <div className={styles.toggle} role="group" aria-label={ariaLabel}>
      {options.map((opt, i) => (
        <button
          key={opt.value}
          ref={(el) => {
            refs.current[i] = el;
          }}
          className={styles.option}
          data-selected={selected === opt.value}
          aria-selected={selected === opt.value}
          aria-pressed={selected === opt.value}
          onClick={() => onSelect(opt.value)}
          onKeyDown={(e) => handleKeyDown(e, i)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
