// How screens reach the data: one source, provided once in main.tsx (contracts/data-access.md,
// Hooks). Components never load data themselves.
import { createContext, use, useEffect, useState, type ReactNode } from "react";
import { buildLandingView } from "./landing";
import type { DataSource, LandingView } from "./types";

const DataSourceContext = createContext<DataSource | null>(null);

export function DataSourceProvider({
  source,
  children,
}: {
  source: DataSource;
  children: ReactNode;
}) {
  return <DataSourceContext value={source}>{children}</DataSourceContext>;
}

export type LandingState =
  { state: "loading" } | { state: "ready"; view: LandingView } | { state: "error" };

async function loadLanding(source: DataSource): Promise<LandingState> {
  const [index, landing, manifest] = await Promise.all([
    source.getIndex(),
    source.getLanding(),
    source.getManifest(),
  ]);
  for (const result of [index, landing, manifest]) {
    if (!result.ok) {
      console.error("Travel Check: showcase data could not be loaded", result.error);
      return { state: "error" };
    }
  }
  if (!index.ok || !landing.ok || !manifest.ok) return { state: "error" };
  const view = buildLandingView(index.value, landing.value, manifest.value);
  if (!view.ok) {
    console.error("Travel Check: showcase data could not be loaded", view.error);
    return { state: "error" };
  }
  return { state: "ready", view: view.value };
}

export function useLandingView(): LandingState {
  const source = use(DataSourceContext);
  if (!source) throw new Error("useLandingView needs a DataSourceProvider");
  const [state, setState] = useState<LandingState>({ state: "loading" });
  useEffect(() => {
    let current = true;
    void loadLanding(source).then((next) => {
      if (current) setState(next);
    });
    return () => {
      current = false;
    };
  }, [source]);
  return state;
}
