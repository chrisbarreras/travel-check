# ADR-0003: DuckDB/Parquet for v1; Postgres only once user data exists

- **Status:** Accepted
- **Date:** 2026-11-24

## Context

The product design doc proposed PostgreSQL/PostGIS. Through Phase 4, though, all data is historical and read-only: BTS flight records, derived itineraries and precomputed risk data. There are no accounts or saved trips. Airport geography is a few hundred points, which needs no spatial database.

## Decision

- Store raw and processed flight data as Parquet files and query them with DuckDB.
- The pipeline writes derived outputs: static JSON in Phase 1, and Parquet or a DuckDB file that the API reads in Phase 2.
- Introduce PostgreSQL only when user data appears (accounts, saved trips, alerts), which is expected in Phase 5.
- Do not use PostGIS; Turf.js and simple coordinates cover the geography.

## Consequences

- There is no database server to run, deploy or pay for in v1.
- Analytical queries over millions of BTS rows run quickly on a laptop.
- The Phase 2 API ships its data inside the deployment (a read-only file), so updating data means redeploying.
- Adding Postgres later is contained, because data access goes through provider interfaces.
