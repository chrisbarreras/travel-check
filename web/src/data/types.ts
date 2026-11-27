// Browser-only types of the data-access module (data-model.md, Web-side types).
import type {
  RouteFile,
  ShowcaseComparison,
  ShowcaseIndex,
  ShowcaseItinerary,
  ShowcaseManifest,
} from "@contract";

export interface DataError {
  kind: "network" | "not_found" | "invalid";
  /** The file's path below data/showcase/, for example "landing.json". */
  file: string;
  /** For the console and tests only; visitors see a plain message. */
  detail: string;
}

export type Result<T> = { ok: true; value: T } | { ok: false; error: DataError };

/** The provider interface: the one place showcase data comes from (FR-011, FR-013). */
export interface DataSource {
  getIndex(): Promise<Result<ShowcaseIndex>>;
  getLanding(): Promise<Result<RouteFile>>;
  getRoute(routeId: string): Promise<Result<RouteFile>>;
  getManifest(): Promise<Result<ShowcaseManifest>>;
}

/** What the landing screen renders: validated and cross-checked. */
export interface LandingView {
  index: ShowcaseIndex;
  landing: RouteFile;
  manifest: ShowcaseManifest;
  comparison: ShowcaseComparison;
  /** The itinerary with the higher rate (`itinerary_a`). */
  a: ShowcaseItinerary;
  b: ShowcaseItinerary;
  /** `manifest.run.run_at`: the contract types `run` loosely, so it is checked here. */
  builtAt: string;
}
