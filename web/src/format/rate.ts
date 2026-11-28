// Wording of rates, excluded days and flight numbers (data-model.md, Fields shown).
import type { ExcludedDays, FindLeg, Rate } from "@contract";
import { percentOf } from "./numbers";

const days = (n: number): string => `${String(n)} ${n === 1 ? "day" : "days"}`;

export type RateText =
  | { kind: "ok"; percent: number; days: number; text: string }
  | { kind: "insufficient"; days: number; text: string };

/** "worked on 92% of 298 days", or "insufficient data (12 days)" below the minimum sample. */
export function rateText(rate: Rate, period?: string): RateText {
  const when = period ? `, ${period}` : "";
  if (rate.status === "insufficient_data" || rate.paired_days === 0) {
    return {
      kind: "insufficient",
      days: rate.paired_days,
      text: `insufficient data (${days(rate.paired_days)}${when})`,
    };
  }
  const percent = percentOf(rate.count_feasible, rate.paired_days);
  return {
    kind: "ok",
    percent,
    days: rate.paired_days,
    text: `worked on ${String(percent)}% of ${days(rate.paired_days)}${when}`,
  };
}

/** One line per non-zero reason a day was not counted. */
export function excludedText(excluded: ExcludedDays): string[] {
  const lines: string[] = [];
  if (excluded.not_connecting > 0) {
    lines.push(`${days(excluded.not_connecting)} the two flights were not scheduled to connect`);
  }
  if (excluded.end_of_period > 0) {
    lines.push(`${days(excluded.end_of_period)} at the end of the data period`);
  }
  if (excluded.quality > 0) {
    lines.push(`${days(excluded.quality)} that failed the data-quality checks`);
  }
  return lines;
}

/**
 * Each leg's most frequent flight number. Schedule-slot itineraries can fly under several
 * numbers (ADR-0014). The share behind "most often" has no published definition, so it is
 * never shown as a number (constitution, Principle I); a note says other numbers were used.
 */
export function flightNumbers(legs: FindLeg[]): { numbers: string[]; varies: boolean } {
  const varies = legs.some((leg) => leg.share_of_days < 0.95);
  return { numbers: legs.map((leg) => leg.flight_number), varies };
}
