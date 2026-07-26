import { Component, type ReactNode } from "react";
import Button from "../Button/Button";
import styles from "./ErrorBoundary.module.css";

interface Props {
  children: ReactNode;
}
interface State {
  hasError: boolean;
}

/** Catches render errors below it so one broken screen shows a recoverable
 * fallback instead of a blank white page. Logging only — no telemetry here. */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught:", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className={styles.wrap} role="alert">
          <p className={styles.message}>Something went wrong on this screen.</p>
          <Button
            variant="primary"
            onClick={() => window.location.reload()}
          >
            Reload
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
