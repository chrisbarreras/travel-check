// Wording of rates, excluded days and flight numbers (data-model.md, Fields shown).
import type { ExcludedDays, FindLeg, Rate } from "@contract";
import { percentOf } from "./numbers";

const days = (n: number): string => `${String(n)} ${n === 1 ? "day" : "days"}`;

export type RateText =
  | { kind: "ok"; percent: number; days: number; text: string }
  | { kind: "insufficient"; days: number; text: string };

/** "worked on 92% of 298 days", or "insufficient data (12 days)" below the minimum sample. */
export function rateText(rate: Rate): RateText {
  if (rate.status === "insufficient_data" || rate.paired_days === 0) {
    return {
      kind: "insufficient",
      days: rate.paired_days,
      text: `insufficient data (${days(rate.paired_days)})`,
    };
  }
  const percent = percentOf(rate.count_feasible, rate.paired_days);
  return {
    kind: "ok",
    percent,
    days: rate.paired_days,
    text: `worked on ${String(percent)}% of ${days(rate.paired_days)}`,
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
 * numbers (ADR-0014), so the share of days is given when it is below 95%.
 */
export function flightNumbers(legs: FindLeg[]): string[] {
  return legs.map((leg) =>
    leg.share_of_days >= 0.95
      ? leg.flight_number
      : `${leg.flight_number} (on ${String(Math.round(leg.share_of_days * 100))}% of days)`,
  );
}
