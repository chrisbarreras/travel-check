// Times, durations and dates for display. The schedule's times are minutes after local
// midnight at each airport, so the browser does no time-zone arithmetic (constitution IV).
import type { DataPeriod } from "@contract";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "12:38 pm", with the number of days after the departure day for times past midnight. */
export function localTime(minutes: number): { text: string; dayOffset: number } {
  if (!Number.isInteger(minutes) || minutes < 0) {
    throw new RangeError(`localTime: invalid minutes ${String(minutes)}`);
  }
  const dayOffset = Math.floor(minutes / 1440);
  const ofDay = minutes % 1440;
  const hour24 = Math.floor(ofDay / 60);
  const minute = ofDay % 60;
  const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12;
  const suffix = hour24 < 12 ? "am" : "pm";
  return {
    text: `${String(hour12)}:${String(minute).padStart(2, "0")} ${suffix}`,
    dayOffset,
  };
}

/**
 * Days between the departure day and the arrival day, both in local time. The schedule gives
 * clock times (0–1439) and the travel time, so the arrival clock minus the departure clock
 * plus travel time is the airports' clock difference, taken within half a day either way.
 * No time-zone data is needed or used.
 */
export function arrivalDayOffset(schedule: {
  dep_local_min: number;
  arr_local_min: number;
  travel_min: number;
}): number {
  const atOriginClock = schedule.dep_local_min + schedule.travel_min;
  const clockDifference =
    ((((schedule.arr_local_min - atOriginClock) % 1440) + 1440 + 720) % 1440) - 720;
  return Math.floor((atOriginClock + clockDifference) / 1440);
}

/** "1 h 39 min", "45 min" or "1 h". */
export function duration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${String(rest)} min`;
  return rest === 0 ? `${String(hours)} h` : `${String(hours)} h ${String(rest)} min`;
}

function calendarDate(text: string): { year: number; month: number; day: number } {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(text);
  const month = Number(match?.[2]);
  const day = Number(match?.[3]);
  if (!match || month < 1 || month > 12 || day < 1 || day > 31) {
    throw new RangeError(`invalid date ${text}`);
  }
  return { year: Number(match[1]), month, day };
}

function monthYear(text: string): string {
  const { year, month } = calendarDate(text);
  return `${MONTHS[month - 1] ?? ""} ${String(year)}`;
}

/** "Jul 2024 – Jun 2025". */
export function periodText(period: DataPeriod): string {
  return `${monthYear(period.start)} – ${monthYear(period.end)}`;
}

/** The UTC calendar date of a timestamp such as "2026-11-26T21:10:45+00:00": "26 Nov 2026". */
export function builtDate(timestamp: string): string {
  const parsed = new Date(timestamp);
  if (!/^\d{4}-\d{2}-\d{2}T/.test(timestamp) || Number.isNaN(parsed.getTime())) {
    throw new RangeError(`builtDate: invalid timestamp ${timestamp}`);
  }
  const month = MONTHS[parsed.getUTCMonth()] ?? "";
  return `${String(parsed.getUTCDate())} ${month} ${String(parsed.getUTCFullYear())}`;
}
