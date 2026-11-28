// Rounding and wording of rates and differences (research R11; docs/methodology.md, Precision).
// Values are rounded half away from zero, as the pipeline does (feature 002, `rate_of_days`).

const MINUS = "−"; // U+2212, as in docs/design.md

/** Whole percent of feasible days, exact integer arithmetic, halves away from zero. */
export function percentOf(feasible: number, paired: number): number {
  if (!Number.isInteger(feasible) || !Number.isInteger(paired) || paired <= 0 || feasible < 0) {
    throw new RangeError(`percentOf: invalid counts ${String(feasible)} of ${String(paired)}`);
  }
  return Math.floor((200 * feasible + paired) / (2 * paired));
}

/**
 * Signed whole points from a stored share (for example 0.283644 is 28 points). Stored values
 * have 6 decimals, so they are converted to integer millionths first, which is exact.
 */
export function points(share: number): number {
  const millionths = Math.round(share * 1_000_000);
  const magnitude = Math.floor((Math.abs(millionths) + 5_000) / 10_000);
  return magnitude === 0 ? 0 : Math.sign(millionths) * magnitude;
}

/** "+28", "−3" or "0". */
export function signed(value: number): string {
  if (value > 0) return `+${String(value)}`;
  if (value < 0) return `${MINUS}${String(-value)}`;
  return "0";
}

/** "95% interval +22 to +35 points". */
export function intervalText(low: number, high: number): string {
  return `95% interval ${signed(points(low))} to ${signed(points(high))} points`;
}

/**
 * Whether the higher itinerary worked more often, decided on the exact interval: only when its
 * lower bound is above zero. Never decided on rounded values (data-model.md).
 */
export function similarOrMore(ciLow: number, ciHigh: number): "more" | "similar" {
  return ciLow > 0 && ciHigh > 0 ? "more" : "similar";
}
