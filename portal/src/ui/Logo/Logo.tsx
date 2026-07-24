import type { SVGProps } from "react";
import styles from "./Logo.module.css";

/**
 * The TerraCipher brand mark: a solid indigo seal with a struck "T" monogram
 * and two earth-strata lines at the base (Terra + Cipher). Self-contained —
 * the disc carries its own indigo fill and a white foreground, so it reads
 * correctly on any surface (light card, dark rail, indigo panel) without a
 * theme override. Pure static geometry (no clipPath / generated ids) so it is
 * deterministic in snapshots and degrades cleanly to a solid disc + T at
 * favicon scale, where the hairline strata drop away.
 *
 * Keep this in exact sync with `public/favicon.svg` — same viewBox and paths.
 */
export default function Logo({
  size = 32,
  title = "TerraCipher",
  ...rest
}: { size?: number; title?: string } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      className={styles.logo}
      width={size}
      height={size}
      viewBox="0 0 100 100"
      role="img"
      aria-label={title}
      {...rest}
    >
      <title>{title}</title>
      <circle cx="50" cy="50" r="48" className={styles.disc} />
      <g className={styles.fg}>
        {/* struck "T" monogram */}
        <rect x="26" y="27" width="48" height="12" rx="2" />
        <rect x="44" y="27" width="12" height="50" rx="2" />
        {/* two earth-strata lines, pre-fitted inside the disc (no clip needed) */}
        <rect x="18" y="80" width="64" height="4.5" rx="1" />
        <rect x="27" y="88" width="46" height="4" rx="1" />
      </g>
    </svg>
  );
}
