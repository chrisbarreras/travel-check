// Risk visuals (spec US2): never color alone; every value is also text.
import type { DisruptionNote, FailureBreakdown, MonthRate } from "@contract";
import { meterDots } from "./meter";
import { monthBars } from "./months";

/** Ten dots filled to the rate's nearest 10%. Decorative: the text beside it carries it. */
export function Meter({ percent }: { percent: number }) {
  const filled = meterDots(percent);
  return (
    <span className="meter" aria-hidden="true" data-filled={filled}>
      {Array.from({ length: 10 }, (_, i) => (
        <span key={i} className={i < filled ? "meter-dot filled" : "meter-dot"} />
      ))}
    </span>
  );
}

const FAILURE_LABELS = {
  too_little_time: "Too little time",
  cancelled: "A leg was cancelled",
  diverted: "A leg was diverted",
} as const;

const FAILURE_HELP = {
  too_little_time: "A longer scheduled layover, or an earlier inbound flight, would have helped.",
  cancelled: "A longer layover would not have helped; a later connection or another hub might.",
  diverted: "Diversions are rare and not helped by a longer layover.",
  none: "Every counted day worked.",
} as const;

/** Why the connection didn't work, by type (FR-005). */
export function FailureBar({ failures }: { failures: FailureBreakdown }) {
  const kinds = ["too_little_time", "cancelled", "diverted"] as const;
  const total = kinds.reduce((sum, k) => sum + failures[k], 0);
  return (
    <div className="failure">
      {total > 0 ? (
        <span className="failure-bar" aria-hidden="true">
          {kinds.map((k) =>
            failures[k] > 0 ? (
              <span
                key={k}
                className={`failure-seg ${k}`}
                style={{ width: `${String((failures[k] / total) * 100)}%` }}
              />
            ) : null,
          )}
        </span>
      ) : null}
      <ul className="failure-legend">
        {kinds.map((k) => (
          <li key={k}>
            <span className={`swatch ${k}`} aria-hidden="true" />
            {FAILURE_LABELS[k]}: {failures[k]} {failures[k] === 1 ? "day" : "days"}
          </li>
        ))}
      </ul>
      <p>{FAILURE_HELP[failures.dominant]}</p>
    </div>
  );
}

/** Twelve labelled monthly bars; counts below the monthly minimum; notes kept apart (FR-006). */
export function MonthChart({
  monthly,
  notes,
}: {
  monthly: readonly MonthRate[];
  notes: readonly DisruptionNote[];
}) {
  const bars = monthBars(monthly, notes);
  const shown = notes.filter((n) => bars.some((b) => b.notes.includes(n.note_id)));
  return (
    <div className="months">
      <ol className="month-bars">
        {bars.map((b) => (
          <li key={b.month} className={`month ${b.kind}`}>
            <span className="month-track" aria-hidden="true">
              {b.kind === "ok" && b.percent !== null ? (
                <span className="month-fill" style={{ height: `${String(b.percent)}%` }} />
              ) : null}
            </span>
            {b.kind === "ok" ? (
              <span className="month-days" aria-hidden="true">
                {b.days} d
              </span>
            ) : null}
            <span className="month-value">
              {b.kind === "ok"
                ? `${String(b.percent)}%`
                : b.kind === "none"
                  ? "–"
                  : `${String(b.days)} d`}
            </span>
            <span className="month-label">
              {b.label}
              {b.notes.length > 0 ? <sup aria-hidden="true"> *</sup> : null}
            </span>
            <span className="visually-hidden">
              {b.kind === "ok"
                ? `: worked on ${String(b.percent)}% of ${String(b.days)} days`
                : b.kind === "none"
                  ? ": no flights"
                  : `: ${String(b.days)} days, too few for a rate`}
              {b.notes.length > 0 ? "; see the notes below" : ""}
            </span>
          </li>
        ))}
      </ol>
      <p className="muted">
        Under each bar: the month&apos;s rate, then the days it is based on (&quot;31 d&quot;).
      </p>
      {bars.some((b) => b.kind === "insufficient") ? (
        <p className="muted">"N d": the days counted in a month with too few for a rate.</p>
      ) : null}
      {shown.length > 0 ? (
        <ul className="notes">
          {shown.map((n) => (
            <li key={n.note_id}>
              <span aria-hidden="true">* </span>
              {n.start} to {n.end}: {n.text}{" "}
              <a href={n.source_url} target="_blank" rel="noopener noreferrer">
                Source
              </a>
              . Not used in any figure.
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
