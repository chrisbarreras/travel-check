import { Component, type ErrorInfo, type ReactNode } from "react";
import { LoadError } from "./LoadError";

/**
 * Any error while rendering shows the plain message instead of a blank page (FR-014). Data
 * problems are normally caught earlier by the data-access module; this is the last guard.
 */
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  override state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  override componentDidCatch(error: unknown, info: ErrorInfo): void {
    console.error("Travel Check: the page could not be shown", error, info.componentStack);
  }

  override render(): ReactNode {
    return this.state.failed ? (
      <main id="main">
        <LoadError />
      </main>
    ) : (
      this.props.children
    );
  }
}
