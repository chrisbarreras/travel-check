import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { builtDate, periodText } from "../../src/format";
import { committedIndex, committedManifest } from "../fixtures/committed";
import { renderApp } from "../fixtures/render";

const index = committedIndex();
const manifest = committedManifest();

describe("the footer (FR-006, FR-007)", () => {
  it("credits every data source verbatim, with links", async () => {
    renderApp();
    const footer = await screen.findByRole("contentinfo");
    for (const attribution of index.attribution) {
      expect(footer).toHaveTextContent(attribution.text);
      expect(footer).toHaveTextContent(attribution.licence);
      const links = within(footer)
        .getAllByRole("link")
        .map((l) => l.getAttribute("href"));
      expect(links).toContain(attribution.url);
    }
  });

  it("states the data period and the build date", async () => {
    renderApp();
    const footer = await screen.findByRole("contentinfo");
    expect(footer).toHaveTextContent(periodText(index.period));
    expect(footer).toHaveTextContent(`Data built ${builtDate(String(manifest.run.run_at))}`);
  });

  it("links to the methodology and the repository", async () => {
    renderApp();
    const footer = await screen.findByRole("contentinfo");
    expect(within(footer).getByRole("link", { name: /methodology/i })).toHaveAttribute(
      "href",
      "https://github.com/chrisbarreras/travel-check/blob/main/docs/methodology.md",
    );
    expect(within(footer).getByRole("link", { name: /source/i })).toHaveAttribute(
      "href",
      "https://github.com/chrisbarreras/travel-check",
    );
  });

  it("carries the copyright line", async () => {
    renderApp();
    const footer = await screen.findByRole("contentinfo");
    expect(footer).toHaveTextContent(
      "© 2026 Christopher T. Barreras Consulting. All rights reserved.",
    );
  });
});
