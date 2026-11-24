# ADR-0001: Ship a static site first; add the API in Phase 2

- **Status:** Accepted
- **Date:** 2026-11-24

## Context

The project's primary goal is a polished, deployed portfolio piece; commercial viability is secondary. Building the backend, the pipeline and the frontend together delays the first presentable result and raises the risk of never finishing. The most visible value, the map-based itinerary comparison, needs only precomputed data for a curated set of routes.

## Decision

- **Phase 1** ships a static site. A Python pipeline precomputes curated itineraries and risk data into JSON files, and the React frontend reads them directly.
- **Phase 2** adds a FastAPI backend that serves **the same response shape** (see [ADR-0007](0007-pydantic-schema-source-of-truth.md)), together with search across any covered route.

## Consequences

- A real-data demo can be deployed for free on static hosting, early in the project.
- Phase 1 alone shows frontend and data work, but is weaker evidence of backend skills until Phase 2 lands.
- Because the JSON matches the future API response, moving to the API is a contained change: replace the file fetch with an API call.
- Features that need on-demand computation over large data, such as arbitrary route search, wait for Phase 2.
