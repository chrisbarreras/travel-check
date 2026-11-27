// Loading and failure states, with only the data source swapped (US3; FR-013, FR-014).
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { memorySource, type DataSource, type Result } from "../../src/data";
import { clone, committedFiles, committedLanding } from "../fixtures/committed";
import { renderApp } from "../fixtures/render";

const MESSAGE = "This example could not be loaded";

/** A source whose answers never arrive. */
const pendingSource: DataSource = {
  getIndex: () => new Promise<never>(() => undefined),
  getLanding: () => new Promise<never>(() => undefined),
  getRoute: () => new Promise<never>(() => undefined),
  getManifest: () => new Promise<never>(() => undefined),
};

/** A source whose every request fails as the network would. */
const failure = <T,>(file: string): Promise<Result<T>> =>
  Promise.resolve({ ok: false, error: { kind: "network", file, detail: "offline" } });
const offlineSource: DataSource = {
  getIndex: () => failure("index.json"),
  getLanding: () => failure("landing.json"),
  getRoute: (id) => failure(id),
  getManifest: () => failure("manifest.json"),
};

function expectNoFigures() {
  const main = screen.getByRole("main");
  expect(main.textContent).not.toMatch(/\d/);
}

describe("page states", () => {
  it("shows the layout's shape and no numbers while loading", () => {
    renderApp(pendingSource);
    expect(screen.getByRole("main")).toHaveAttribute("aria-busy", "true");
    expect(screen.getByTestId("skeleton")).toBeInTheDocument();
    expectNoFigures();
    expect(screen.queryByText(MESSAGE, { exact: false })).not.toBeInTheDocument();
  });

  it("shows the plain message and no figures when the network fails", async () => {
    renderApp(offlineSource);
    expect(await screen.findByText(MESSAGE, { exact: false })).toBeInTheDocument();
    expectNoFigures();
  });

  it("shows the plain message for a malformed landing file", async () => {
    const files = committedFiles();
    files["landing.json"] = { ...committedLanding(), itineraries: "not a list" };
    renderApp(memorySource(files));
    expect(await screen.findByText(MESSAGE, { exact: false })).toBeInTheDocument();
    expectNoFigures();
  });

  it("shows the plain message when the landing comparison is missing", async () => {
    const files = committedFiles();
    files["landing.json"] = { ...clone(committedLanding()), comparisons: [] };
    renderApp(memorySource(files));
    expect(await screen.findByText(MESSAGE, { exact: false })).toBeInTheDocument();
    expectNoFigures();
  });

  it("renders the example from the same App with the committed source", async () => {
    renderApp(memorySource(committedFiles()));
    expect(await screen.findByRole("heading", { level: 2 })).toBeInTheDocument();
    expect(screen.queryByText(MESSAGE, { exact: false })).not.toBeInTheDocument();
  });
});
