# ADR-0010: The current selection lives in the URL

- **Status:** Accepted
- **Date:** 2026-11-24

## Context

The map, itinerary list and timeline must always show the same selection. Keeping three copies of that state in sync is error-prone. A portfolio demo also benefits from links that open directly on a specific, striking example.

## Decision

- The **URL query string is the single source of truth** for the current selection, for example `?route=RDM-BOS&itinerary=2`, plus adjustable settings such as transfer time.
- The map, list and timeline all read the selection from the URL and update it on user interaction.
- Invalid or outdated parameters fall back to a sensible default view, never to an error page.

## Consequences

- The three views can't disagree, because they share one source.
- Any view can be shared or bookmarked, and the README and resume can link straight to a showcase example.
- The browser's back and forward buttons move through selections, which must be checked so it doesn't feel jumpy (for example, by replacing history entries for slider changes rather than adding them).
- Parameter names become a small public interface and should stay stable once links are shared.
