import { render } from "@testing-library/react";
import { App } from "../../src/App";
import { ErrorBoundary } from "../../src/components/ErrorBoundary";
import { DataSourceProvider, memorySource, type DataSource } from "../../src/data";
import { committedFiles } from "./committed";

/** Renders the whole app over a data source (the committed files by default). */
export function renderApp(source: DataSource = memorySource(committedFiles())) {
  return render(
    <ErrorBoundary>
      <DataSourceProvider source={source}>
        <App />
      </DataSourceProvider>
    </ErrorBoundary>,
  );
}
