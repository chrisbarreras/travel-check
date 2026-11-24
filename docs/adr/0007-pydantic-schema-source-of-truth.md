# ADR-0007: Pydantic models are the single definition of the data shape

- **Status:** Accepted
- **Date:** 2026-11-24

## Context

The pipeline (Python) writes the data, the frontend (TypeScript) reads it, and from Phase 2 the API (Python) serves it. If each defines the shape separately, they drift apart and the frontend breaks without warning.

## Decision

- Define the data shapes (itineraries, legs, airports, risk distributions and so on) **once, as Pydantic models** in a shared Python package.
- The **pipeline** validates its output against these models when writing the Phase 1 JSON.
- The **API** (Phase 2) uses the same models for its responses.
- **TypeScript types are generated** from the models: from their JSON Schema in Phase 1, and from FastAPI's OpenAPI schema in Phase 2. Generated types are never edited by hand.
- A check that the generated types are up to date runs in CI.

## Consequences

- Changing the data shape becomes a type error in the frontend instead of a runtime bug.
- The Phase 1 static JSON and the Phase 2 API responses are guaranteed to have the same shape.
- Changes to the schema always start in Python, then types are regenerated, which adds a small step to frontend work.
