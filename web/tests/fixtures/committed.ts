// The committed showcase files, read from disk for tests that run in Node (no network).
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import type { RouteFile, ShowcaseIndex, ShowcaseManifest } from "@contract";

// Vitest and Playwright run from web/.
export const showcaseDir = join(process.cwd(), "..", "site-data", "showcase");

function read(path: string): unknown {
  return JSON.parse(readFileSync(join(showcaseDir, path), "utf8"));
}

/** Every committed file, keyed by its path below data/showcase/. */
export function committedFiles(): Record<string, unknown> {
  const files: Record<string, unknown> = {
    "index.json": read("index.json"),
    "landing.json": read("landing.json"),
    "manifest.json": read("manifest.json"),
  };
  for (const name of readdirSync(join(showcaseDir, "routes"))) {
    files[`routes/${name}`] = read(`routes/${name}`);
  }
  return files;
}

export const committedIndex = (): ShowcaseIndex => read("index.json") as ShowcaseIndex;
export const committedLanding = (): RouteFile => read("landing.json") as RouteFile;
export const committedManifest = (): ShowcaseManifest => read("manifest.json") as ShowcaseManifest;

/** A deep copy that a test may change freely. */
export function clone<T>(value: T): T {
  return structuredClone(value);
}
