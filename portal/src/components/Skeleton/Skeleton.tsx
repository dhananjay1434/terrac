import clsx from "clsx";
import styles from "./Skeleton.module.css";

export type SkeletonVariant = "text" | "number" | "row" | "card";

/**
 * Loading placeholder block. The pulse animation is disabled globally by the
 * prefers-reduced-motion override in styles.css.
 */
export default function Skeleton({
  variant = "text",
}: {
  variant?: SkeletonVariant;
}) {
  return <div aria-hidden className={clsx(styles.skeleton, styles[variant])} />;
}
