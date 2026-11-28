// The monthly view's bars (docs/design.md, Month chart; spec Clarifications).
import type { DisruptionNote, MonthRate } from "@contract";
import { percentOf } from "../format";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export interface MonthBar {
  month: string;
  label: string;
  kind: "ok" | "insufficient" | "none";
  /** Whole percent; only for months with a rate. */
  percent: number | null;
  days: number;
  /** Ids of the disruption notes that cover the month. */
  notes: string[];
}

function label(month: string): string {
  const [year = "", m = "1"] = month.split("-");
  return `${MONTHS[Number(m) - 1] ?? ""} ${year}`;
}

export function monthBars(
  monthly: readonly MonthRate[],
  notes: readonly DisruptionNote[],
): MonthBar[] {
  const known = new Set(notes.map((n) => n.note_id));
  return monthly.map((m) => {
    const kind = m.status === "ok" ? "ok" : m.status === "no_flights" ? "none" : "insufficient";
    return {
      month: m.month,
      label: label(m.month),
      kind,
      percent:
        kind === "ok" && m.rate !== null
          ? percentOf(Math.round(m.rate * m.paired_days), m.paired_days)
          : null,
      days: m.paired_days,
      notes: m.note_ids.filter((id) => known.has(id)),
    };
  });
}
