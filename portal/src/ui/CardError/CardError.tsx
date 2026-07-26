import type { ReactNode } from "react";
import Card from "../Card/Card";
import Button from "../Button/Button";
import styles from "./CardError.module.css";

/** The one fetch-failure card: message + retry. Audit D5. */
export default function CardError({
  message,
  onRetry,
  children,
}: {
  message: ReactNode;
  onRetry?: () => void;
  children?: ReactNode;
}) {
  return (
    <Card className={styles.card}>
      <span className={styles.message}>{message}</span>
      {children}
      {onRetry && (
        <Button variant="neutral" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </Card>
  );
}
