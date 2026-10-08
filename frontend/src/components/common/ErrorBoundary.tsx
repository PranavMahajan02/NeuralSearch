import { Component, type ErrorInfo, type ReactNode } from "react";

interface State {
  error: Error | null;
}

/** Catches render errors below it and shows a friendly fallback instead of a blank page. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo): void {
    // Errors are shown in the UI; no client-side logging service is configured.
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div role="alert" className="mx-auto max-w-lg px-6 py-24 text-center">
        <h1 className="text-xl font-semibold">Something went wrong</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          This page hit an unexpected error. Your files and index are not affected.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <button
            type="button"
            onClick={() => this.setState({ error: null })}
            className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800"
          >
            Try again
          </button>
          <a
            href="/search"
            className="rounded-lg px-4 py-2 text-sm font-semibold text-blue-800 ring-1 ring-slate-300 dark:text-blue-300"
          >
            Go to search
          </a>
        </div>
      </div>
    );
  }
}
