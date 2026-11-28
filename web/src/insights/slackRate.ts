// The connection-feasibility rule, recomputed in the browser from the published daily slack
// (ADR-0006). The rule and its cases are shared with the pipeline:
// shared/test-cases/slack-feasibility.json (constitution, Principle II).
import type { DailySeries } from "@contract";

export interface SlackRate {
  paired_days: number;
  count_feasible: number;
  status: "ok" | "insufficient_data";
  rate: number | null;
}

/** count / paired to 6 decimals, halves away from zero, as the pipeline stores rates. */
function sixDecimals(count: number, paired: number): number {
  return Math.floor((2 * count * 1_000_000 + paired) / (2 * paired)) / 1_000_000;
}

/**
 * A day is feasible when neither leg was cancelled (C) or diverted (D) and its slack is at
 * least the transfer time plus the boarding cutoff. Every paired day counts in the sample.
 */
export function slackRate(
  daily: Pick<DailySeries, "outcome" | "slack_min"> & { day_offset?: number[] },
  transferMin: number,
  cutoffMin: number,
  minSampleDays: number,
): SlackRate {
  const threshold = transferMin + cutoffMin;
  const paired = daily.slack_min.length;
  let feasible = 0;
  daily.slack_min.forEach((slack, i) => {
    const code = daily.outcome[i];
    if (code !== "C" && code !== "D" && slack !== null && slack >= threshold) feasible += 1;
  });
  const ok = paired >= minSampleDays && paired > 0;
  return {
    paired_days: paired,
    count_feasible: feasible,
    status: ok ? "ok" : "insufficient_data",
    rate: ok ? sixDecimals(feasible, paired) : null,
  };
}
