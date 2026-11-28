/** Filled dots of the 10-dot reliability meter: the rate to the nearest 10%, halves up. */
export function meterDots(rate: number): number {
  return Math.floor((Math.round(rate * 1_000_000) + 50_000) / 100_000);
}
