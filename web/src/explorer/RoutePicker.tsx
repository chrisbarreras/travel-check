import type { AirportInfo, ShowcaseIndex } from "@contract";

export function airportLabel(airports: readonly AirportInfo[], code: string): string {
  const a = airports.find((x) => x.code === code);
  return a ? `${a.city} (${code})` : code;
}

/** Chooses one of the showcase routes (FR-004): a native select, keyboard and screen-reader ready. */
export function RoutePicker({
  index,
  routeId,
  onChoose,
}: {
  index: ShowcaseIndex;
  routeId: string;
  onChoose: (routeId: string) => void;
}) {
  const label = (code: string) => airportLabel(index.airports, code);
  const routes = [...index.routes].sort(
    (a, b) =>
      label(a.origin).localeCompare(label(b.origin)) || label(a.dest).localeCompare(label(b.dest)),
  );
  return (
    <div className="route-picker">
      <label htmlFor="route-picker">Route</label>
      <select
        id="route-picker"
        value={routeId}
        onChange={(e) => {
          onChoose(e.target.value);
        }}
      >
        {routes.map((r) => (
          <option key={r.route_id} value={r.route_id}>
            {label(r.origin)} to {label(r.dest)}
          </option>
        ))}
      </select>
    </div>
  );
}
