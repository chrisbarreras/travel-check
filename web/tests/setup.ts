import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// jsdom has no WebGL, so component tests use a stand-in map. The explorer's tests replace it
// with one that can select; the real map is covered by the end-to-end tests.
vi.mock("../src/map/MapView", () => ({ default: () => null }));

// jsdom does not lay out pages, so it has no scrollIntoView.
Element.prototype.scrollIntoView = () => undefined;

afterEach(() => {
  cleanup();
});
