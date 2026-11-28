// Loading and failure states, with only the data source swapped (US3; FR-013, FR-014).
import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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

  it("keeps the footer's copyright and links in the loading and error states", async () => {
    for (const source of [pendingSource, offlineSource]) {
      const { unmount } = renderApp(source);
      const footer = await screen.findByRole("contentinfo");
      expect(footer).toHaveTextContent("© 2026 Christopher T. Barreras Consulting");
      expect(footer).toHaveTextContent("Source code");
      unmount();
    }
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

  it("shows the plain message, not a blank page, when rendering throws", async () => {
    // Valid data, but reading one value throws while the cards render: an unexpected bug.
    const source = memorySource(committedFiles());
    const original = source.getLanding.bind(source);
    source.getLanding = async () => {
      const result = await original();
      if (result.ok) {
        for (const itinerary of result.value.itineraries) {
          Object.defineProperty(itinerary.schedule, "travel_min", {
            get() {
              throw new Error("render-time failure");
            },
          });
        }
      }
      return result;
    };
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    renderApp(source);
    expect(await screen.findByText(MESSAGE, { exact: false })).toBeInTheDocument();
    expect(screen.getByRole("main").textContent).not.toMatch(/\d/);
    expect(screen.getByRole("contentinfo")).toHaveTextContent("All rights reserved");
    quiet.mockRestore();
  });

  it("renders the example from the same App with the committed source", async () => {
    renderApp(memorySource(committedFiles()));
    expect(await screen.findByRole("heading", { level: 2 })).toBeInTheDocument();
    expect(screen.queryByText(MESSAGE, { exact: false })).not.toBeInTheDocument();
  });
});
