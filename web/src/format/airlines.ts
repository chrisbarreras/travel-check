// Display names for the airlines that can appear in the showcase (data-model.md, Airline
// names). The data carries codes only; a missing name falls back to the code.
const NAMES: Readonly<Record<string, string>> = {
  AA: "American",
  AS: "Alaska",
  B6: "JetBlue",
  DL: "Delta",
  F9: "Frontier",
  G4: "Allegiant",
  HA: "Hawaiian",
  NK: "Spirit",
  UA: "United",
  WN: "Southwest",
};

export function airlineName(code: string): string {
  return NAMES[code] ?? code;
}
