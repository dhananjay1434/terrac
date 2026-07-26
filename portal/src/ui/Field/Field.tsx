import { cloneElement, isValidElement, useId, type ReactElement, type ReactNode } from "react";
import styles from "./Field.module.css";

/**
 * The one label+control stack. Renders label (with required mark), the
 * control, an optional hint, and an optional error line wired to the
 * control via aria-describedby/aria-invalid. Audit P5.1.
 */
export default function Field({
  label,
  htmlFor,
  required = false,
  hint,
  error,
  children,
}: {
  label: ReactNode;
  htmlFor: string;
  required?: boolean;
  hint?: string;
  error?: string | null;
  children: ReactElement;
}) {
  const errId = useId();
  const control =
    error && isValidElement(children)
      ? cloneElement(children as ReactElement<Record<string, unknown>>, {
          "aria-invalid": true,
          "aria-describedby": errId,
        })
      : children;
  return (
    <div className={styles.field}>
      <label className="micro" htmlFor={htmlFor}>
        {label}
        {required && <span className={styles.required} aria-hidden> *</span>}
      </label>
      {control}
      {hint && !error && <span className={styles.hint}>{hint}</span>}
      {error && (
        <span id={errId} role="alert" className={styles.error}>
          {error}
        </span>
      )}
    </div>
  );
}
