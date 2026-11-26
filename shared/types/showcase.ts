/* Generated from shared/schemas/showcase.schema.json by json-schema-to-typescript@15.0.4 (`flight-pipeline schemas`). Do not edit. */

/**
 * Published showcase files (specs/002-showcase-data-pipeline contracts/outputs.md). Generated from flight_pipeline.showcase.models; do not edit.
 */
export interface Showcase {
  [k: string]: unknown;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "AirlineCoverage".
 */
export interface AirlineCoverage {
  airline: string;
  itineraries: number;
  note: string;
  sold_passengers: number;
}
/**
 * A faster comparable itinerary whose feasibility is shown, by the paired interval, to
 * be no more than the margin worse (research R8).
 *
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "Alternative".
 */
export interface Alternative {
  ci_high: number;
  ci_low: number;
  itinerary_id: string;
  minutes_saved: number;
  rate_other: number;
  rate_this: number;
  shared_days: number;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "Assumptions".
 */
export interface Assumptions {
  boarding_cutoff_min: number;
  buffer_share: number;
  faster_margin: number;
  faster_min_saving_min: number;
  min_connection_default_min: number;
  min_connection_partner_min: number;
  min_sample_days: number;
  monthly_min_sample: number;
  recurrence_threshold: number;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "Attribution".
 */
export interface Attribution {
  licence: string;
  source: string;
  text: string;
  url: string;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "Buffer".
 */
export interface Buffer {
  actual_layover_min: number;
  needed_layover_min: number | null;
  operated_days: number;
  share: number;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "ConnectingOption".
 */
export interface ConnectingOption {
  better: boolean;
  ci_high: number | null;
  ci_low: number | null;
  itinerary_id: string;
  outbound_dep_local_min: number;
  rate: Rate;
}
/**
 * Connection feasibility with its sample. The data period is the file's ``period``.
 *
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "Rate".
 */
export interface Rate {
  count_feasible: number;
  definition: "connection_feasibility";
  paired_days: number;
  rate: number | null;
  status: "ok" | "insufficient_data";
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "Coverage".
 */
export interface Coverage {
  airlines: AirlineCoverage[];
  hubs: string[];
  not_covered: NotCovered[];
  period: DataPeriod;
  routes: string[];
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "NotCovered".
 */
export interface NotCovered {
  kind:
    | "international"
    | "two_or_more_stops"
    | "separate_tickets"
    | "non_reporting_airline"
    | "outside_period"
    | "not_in_showcase";
  text: string;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "DataPeriod".
 */
export interface DataPeriod {
  db1b_quarters: string[];
  end: string;
  start: string;
}
/**
 * One entry per paired day: offset from the period start, actual slack in whole minutes
 * (null for cancelled or diverted days) and an outcome code (F feasible, T too little time,
 * C cancelled, D diverted), compact for the transfer-time slider (ADR-0006).
 *
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "DailySeries".
 */
export interface DailySeries {
  day_offset: number[];
  outcome: string;
  slack_min: (number | null)[];
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "Definition".
 */
export interface Definition {
  key: string;
  methodology_anchor: string;
  text: string;
}
/**
 * A known event shown beside measured values; never used in a calculation.
 *
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "DisruptionNote".
 */
export interface DisruptionNote {
  airlines: string[];
  airports: string[];
  end: string;
  note_id: string;
  source_url: string;
  start: string;
  text: string;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "ExcludedDays".
 */
export interface ExcludedDays {
  end_of_period: number;
  not_connecting: number;
  quality: number;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "FailureBreakdown".
 */
export interface FailureBreakdown {
  cancelled: number;
  diverted: number;
  dominant: "too_little_time" | "cancelled" | "diverted" | "none";
  too_little_time: number;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "FindLeg".
 */
export interface FindLeg {
  flight_number: string;
  share_of_days: number;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "FindParams".
 */
export interface FindParams {
  airlines: string[];
  dest: string;
  legs: FindLeg[];
  origin: string;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "LandingRef".
 */
export interface LandingRef {
  comparison_id: string;
  reason: string;
  route_id: string;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "ManifestRef".
 */
export interface ManifestRef {
  code_version: string;
  config_sha256: string;
  generated: string;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "MonthRate".
 */
export interface MonthRate {
  month: string;
  note_ids: string[];
  paired_days: number;
  rate: number | null;
  status: "ok" | "insufficient_data" | "no_flights";
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "RouteFile".
 */
export interface RouteFile {
  comparisons: ShowcaseComparison[];
  disruption_notes: DisruptionNote[];
  itineraries: ShowcaseItinerary[];
  period: DataPeriod;
  route_id: string;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "ShowcaseComparison".
 */
export interface ShowcaseComparison {
  ci_high: number;
  ci_low: number;
  comparison_id: string;
  cross_hub: boolean;
  difference: number;
  itinerary_a: string;
  itinerary_b: string;
  landing: boolean;
  missing_settings_note: string;
  settings_compared: number;
  shared_days: number;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "ShowcaseItinerary".
 */
export interface ShowcaseItinerary {
  airline: string;
  airline_out: string;
  buffer: Buffer;
  connecting_options: ConnectingOption[];
  daily: DailySeries;
  excluded_days: ExcludedDays;
  failures: FailureBreakdown;
  faster_alternatives: Alternative[];
  find: FindParams;
  hub: string;
  itinerary_id: string;
  monthly: MonthRate[];
  partner_connection: boolean;
  result: Rate;
  schedule: Schedule;
  schedule_warnings: ScheduleWarnings;
  sold: SoldRouting;
  tight_layover: boolean;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "Schedule".
 */
export interface Schedule {
  arr_local_min: number;
  dep_local_min: number;
  layover_min: number;
  nonstop_median_min: number | null;
  nonstop_ratio: number | null;
  travel_min: number;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "ScheduleWarnings".
 */
export interface ScheduleWarnings {
  changes: ScheduleChange[];
  connect_share: number;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "ScheduleChange".
 */
export interface ScheduleChange {
  date: string;
  from_local_min: number;
  leg: "inbound" | "outbound";
  to_local_min: number;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "SoldRouting".
 */
export interface SoldRouting {
  passengers: number;
  routing_itineraries: number;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "RouteSummary".
 */
export interface RouteSummary {
  comparison_count: number;
  dest: string;
  file: string;
  itinerary_count: number;
  nonstop_median_min: number | null;
  origin: string;
  regional_origin: boolean;
  route_id: string;
  share_of_showcase: number;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "ShowcaseIndex".
 */
export interface ShowcaseIndex {
  assumptions: Assumptions;
  attribution: Attribution[];
  coverage: Coverage;
  definitions: Definition[];
  landing: LandingRef;
  manifest: ManifestRef;
  period: DataPeriod;
  routes: RouteSummary[];
  schema_version: string;
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "ShowcaseManifest".
 */
export interface ShowcaseManifest {
  code_version: string;
  config_sha256: string;
  git_commit: string;
  notes_sha256: string;
  outputs: {
    [k: string]: string;
  };
  packages: {
    [k: string]: string;
  };
  run: {
    [k: string]: unknown;
  };
  sources: SourceRecord[];
}
/**
 * This interface was referenced by `Showcase`'s JSON-Schema
 * via the `definition` "SourceRecord".
 */
export interface SourceRecord {
  name: string;
  pinned: boolean;
  sha256: string;
}
