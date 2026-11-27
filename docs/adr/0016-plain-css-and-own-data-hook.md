# ADR-0016: Plain CSS with design tokens, and no data-fetching library, until a measured need

- **Status:** Accepted (2026-11-27, with feature 003, `web-foundation`, after its independent review). Supersedes the rows "UI components and styling" (shadcn/ui and Tailwind CSS) and "Data fetching" (TanStack Query) of [ADR-0002](0002-technology-stack.md).
- **Date:** 2026-11-27

## Context

ADR-0002 chose shadcn/ui with Tailwind CSS for components and styling, and TanStack Query for data fetching, before any interface existed. The first web feature builds one page:
- a handful of cards, a native disclosure and a footer;
- data from three static JSON files, loaded once.

Its budgets are strict: scripts at most 150 KB gzip and Lighthouse performance at least 0.90 on a throttled phone. Its accessibility rules come from [docs/design.md](../design.md). The constitution asks for the simplest thing that meets the spec, with any added complexity justified (Principle VI).

## Decision

- **Styling:** plain CSS. The color tokens of docs/design.md are CSS custom properties in `web/src/styles/tokens.css`, and the layout and components are in `web/src/styles/global.css`. No component library and no utility-class framework.
- **Controls:** native HTML elements (`details`, `summary`, `a`, `button`), which are accessible without extra code.
- **Data fetching:** the data-access module `web/src/data/` (a `DataSource` interface) with one small React hook. It validates each file and caches it in memory for the page load. No data-fetching library.

## When to revisit

- **Styling:** when `explorer-core` or `explorer-insights` needs composite interactive widgets that native elements don't provide accessibly, such as a combobox, tabs with roving focus or a dialog. The first candidate is shadcn/ui's Radix-based components, adopted per component, with Tailwind only if the token CSS becomes the harder path. Adopting them takes a new ADR.
- **Data fetching:** when Phase 2's API brings request states worth a library: retries, invalidation, pagination and stale data. The `DataSource` interface is the swap point, so screens don't change.

## Consequences

- **Small and dependency-light.** The page meets its budgets (85 KB of scripts, gzip) with React as the only runtime library. The styles map one to one to docs/design.md.
- **Hand-written components.** Later features write any component they need, or adopt a library through the new ADR this one requires. There is a single styling system until then.
- **Caching only within a page load.** Fine for static files that change only with a new deployment.
