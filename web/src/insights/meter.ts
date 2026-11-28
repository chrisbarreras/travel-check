/**
 * Filled dots of the 10-dot reliability meter, from the whole percent shown beside it, so
 * the dots never disagree with the text: 95% fills 10, 94% fills 9.
 */
export function meterDots(percent: number): number {
  return Math.floor((percent + 5) / 10);
}
