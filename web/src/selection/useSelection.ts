// Applies the address to the views (ADR-0010): choices add a history entry, corrections
// replace the current one, and back and forward move between selections.
import { useCallback, useEffect, useState } from "react";
import { parseSelection, serializeSelection, type Selection } from "./url";

interface IndexLike {
  routes: readonly { route_id: string }[];
  landing: { route_id: string };
}

export function useSelection(index: IndexLike): {
  selection: Selection;
  note: string | null;
  choose: (next: Selection) => void;
  correct: (next: Selection, note: string | null) => void;
} {
  const read = useCallback(() => parseSelection(window.location.search, index), [index]);
  const [state, setState] = useState(read);

  const write = useCallback(
    (next: Selection, mode: "push" | "replace") => {
      const search = serializeSelection(next, index.landing.route_id);
      const url = `${window.location.pathname}${search}${window.location.hash}`;
      if (mode === "push") window.history.pushState(null, "", url);
      else window.history.replaceState(null, "", url);
    },
    [index],
  );

  // A link that fell back is corrected in place, without a new history entry.
  useEffect(() => {
    if (state.note !== null) write(state.selection, "replace");
    // Only on first load: later notes come from `correct`, which writes itself.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const onPop = () => {
      setState(read());
    };
    window.addEventListener("popstate", onPop);
    return () => {
      window.removeEventListener("popstate", onPop);
    };
  }, [read]);

  const choose = useCallback(
    (next: Selection) => {
      write(next, "push");
      setState({ selection: next, note: null });
    },
    [write],
  );

  const correct = useCallback(
    (next: Selection, note: string | null) => {
      write(next, "replace");
      setState({ selection: next, note });
    },
    [write],
  );

  return { selection: state.selection, note: state.note, choose, correct };
}
