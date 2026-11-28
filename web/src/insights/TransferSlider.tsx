// The transfer-time slider (spec US1): the rate recomputed in the browser from daily slack.
import type { ShowcaseIndex, ShowcaseItinerary } from "@contract";
import { useCallback, useEffect, useId, useState } from "react";
import { rateText } from "../format";
import {
  parseTransfer,
  TRANSFER_MAX,
  TRANSFER_MIN,
  TRANSFER_STEP,
  withTransfer,
} from "../selection/transfer";
import { slackRate } from "./slackRate";
import { Meter } from "./Visuals";

/** The setting from the address, kept in it with replaceState (FR-003). */
function useTransfer(defaultValue: number): [number, (value: number) => void] {
  const [value, setValue] = useState(() => parseTransfer(window.location.search) ?? defaultValue);
  useEffect(() => {
    const onPop = () => {
      setValue(parseTransfer(window.location.search) ?? defaultValue);
    };
    window.addEventListener("popstate", onPop);
    return () => {
      window.removeEventListener("popstate", onPop);
    };
  }, [defaultValue]);
  const set = useCallback(
    (next: number) => {
      const search = withTransfer(window.location.search, next, defaultValue);
      window.history.replaceState(
        window.history.state,
        "",
        `${window.location.pathname}${search}${window.location.hash}`,
      );
      setValue(next);
    },
    [defaultValue],
  );
  return [value, set];
}

export function TransferSlider({
  itinerary,
  index,
  period,
}: {
  itinerary: ShowcaseItinerary;
  index: ShowcaseIndex;
  period: string;
}) {
  const id = useId();
  const cutoff = index.assumptions.boarding_cutoff_min;
  const [transfer, setTransfer] = useTransfer(itinerary.min_connection_min);
  const result = slackRate(itinerary.daily, transfer, cutoff, index.assumptions.min_sample_days);
  const text = rateText(
    {
      status: result.status,
      rate: result.rate,
      paired_days: result.paired_days,
      count_feasible: result.count_feasible,
      definition: "connection_feasibility",
    },
    period,
  );
  return (
    <section className="slider" aria-labelledby={`${id}-heading`}>
      <h4 id={`${id}-heading`}>Your transfer time</h4>
      <label htmlFor={`${id}-range`}>
        Time you need to change planes: <strong>{transfer} min</strong>, plus the {cutoff}-minute
        boarding cutoff
      </label>
      <input
        id={`${id}-range`}
        type="range"
        min={TRANSFER_MIN}
        max={TRANSFER_MAX}
        step={TRANSFER_STEP}
        value={transfer}
        aria-valuetext={`${String(transfer)} minutes`}
        onChange={(e) => {
          setTransfer(Number(e.target.value));
        }}
      />
      <p className="slider-result" aria-live="polite">
        {text.kind === "ok" ? <Meter percent={text.percent} /> : null}
        <span>
          With {transfer} minutes: {text.text}
          {transfer === itinerary.min_connection_min ? " (the published figure)" : ""}
        </span>
      </p>
    </section>
  );
}
