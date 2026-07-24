import { forwardRef, type ElementType, type HTMLAttributes, type ReactNode } from "react";
import clsx from "clsx";
import styles from "./Card.module.css";

export interface CardProps extends HTMLAttributes<HTMLElement> {
  as?: ElementType;
  children?: ReactNode;
}

/** Reusable surface matching the existing `.card` look via tokens:
 * surface-card background, hairline border, r-lg radius, shadow-sm,
 * space-5 padding. Additive — existing `.card` usages are untouched. */
const Card = forwardRef<HTMLElement, CardProps>(function Card(
  { as: Tag = "div", className, children, ...rest },
  ref,
) {
  return (
    <Tag ref={ref} className={clsx(styles.card, className)} {...rest}>
      {children}
    </Tag>
  );
});

export default Card;
