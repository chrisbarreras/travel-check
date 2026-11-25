# Design

The visual and interaction direction for the explorer, from Phase 1 on. It is based on the clickable mockup made after Phase 0 (a private Claude artifact, [Flight reliability explorer mockup](https://claude.ai/artifact/PiXQPZeK75Z6boeKrgTH7C); it shows real Phase 0 data for LaGuardia → Orlando). Feature specs refer to this document; a change to it is a deliberate design decision, reviewed like code.

The constitution's Principles I (statistical honesty) and V (accessible and clear) are the rules this document applies.

## Principles

1. **One question per screen.** "How often did this connection work, and is there a better one?" Everything else is secondary.
2. **Every number explains itself.** A rate always comes with its sample size and period ("Worked 93% of 314 days, Jul 2024 – Jun 2025"). Wording is historical: "worked on X% of days", never "X% chance" or "will make it".
3. **Never color alone.** Every state that matters (reliability, tight layover, selection, failure type) is also shown by text, shape, pattern or position.
4. **Advice only from evidence.** A suggestion (faster alternative, better connecting flight, time of day) appears only when the data for that route supports it, with its interval or count shown; otherwise the panel says there is none.
5. **Calm, dense, readable.** A light, neutral ground, one accent, generous spacing; no gradients, decorative imagery or emoji.

## Screens

| Screen | Purpose | Phase |
|---|---|---|
| **Route explorer** | Map, itinerary list and detail for one origin/destination pair; the landing view opens on one striking example | 1 |
| **Itinerary detail** | Rate, sample, schedule, and the traveler-insight panels for the selected itinerary | 1 |
| **Search** | Two tabs, *Browse flights* (from, to, date, filters) and *Paste from another site*, leading to the same results list | 2 |
| **How the numbers work** | Plain-language methodology with links to `docs/methodology.md` | 1 |

Layout: a header with the route and data period; on wide screens the map and itinerary list side by side, with the detail panel below; on phones everything stacks, the map collapses, and the selected itinerary expands in place. Content width is capped at about 1360 px.

## Color

| Token | Value | Use | Contrast |
|---|---|---|---|
| `ground` | `#F4F6F9` | Page background | |
| `surface` | `#FFFFFF` | Cards, panels | |
| `ink` | `#15202B` | Body text, filled meter dots, primary dark buttons | 16.5:1 on surface, 15.2:1 on ground |
| `muted` | `#4A5868` | Secondary text | 7.3:1 on surface, 6.7:1 on ground |
| `border` | `#DCE2EA` | Card and panel borders (decorative) | |
| `control-border` | `#8794A3` | Input borders, empty meter dots | 3.1:1 on surface (non-text minimum 3:1) |
| `accent` | `#1C56C2` | Links, primary buttons, selection, map routes | 6.7:1 on surface; white text on accent 6.7:1 |
| `accent-strong` / `accent-tint` | `#123E8F` / `#EAF1FD` | Hover; selected card and positive notices | 8.8:1 |
| `warn-text` / `warn-tint` | `#8A3F00` / `#FFF1E3` | Warnings such as "Tight layover" | 6.8:1 |
| `warn-mark` | `#C2560E` | Low-month bars, the cancelled segment (always with a pattern or label) | 4.5:1 on surface |
| `hub-2` | `#6B4FA8` | A second hub's route on the map | 5.7:1 on the map ground |

Blue and orange, not red and green, carry "good" and "watch out", and they also differ in lightness. Values that must be told apart never rely on hue alone.

## Typography

- **Headings:** Space Grotesk, 600–700.
- **Body and data:** Inter, 400–700, 15 px base, line height about 1.45.
- **Numbers:** whole percent for rates and whole points for differences (methodology, "Precision"); tabular figures where numbers stack.

Both fonts are SIL Open Font License, served from Google Fonts or self-hosted.

## Components

- **Itinerary card:** times and duration, flight numbers, airline and hub, the reliability meter, "Worked X% of N days", and badges. The whole card is one button; the selected card gets the accent border and tint, plus `aria-pressed` or `aria-expanded`.
- **Reliability meter:** 10 dots, filled to the rate rounded to the nearest 10%, always next to the exact text rate. The dots are decorative (`aria-hidden`); the text carries the meaning.
- **Badges:** pill with icon and text, for example "Tight layover" (scheduled layover below minimum connection time plus boarding cutoff).
- **Insight panels**, each with an icon and heading: *Faster, just as reliable*; *Better connecting flight*; *Buffer you needed*; *Why it didn't work*; *By month*; *About this itinerary* (connecting days, sold-routing note, how to read the number). A panel with nothing to suggest says so plainly.
- **Failure bar:** too little time (solid), cancelled (striped), diverted (light), always with the counts in text.
- **Month chart:** 12 bars, each labelled with its value; months with no flights show a dash. Known events (for example the July 2024 CrowdStrike outage) appear as a separate note, never inside the measured values.
- **"Find this itinerary":** a primary link button that opens a prefilled search in a new tab, with a note that prices come from that site and the app neither sees nor stores them.
- **Search controls:** labelled selects, date input and checkboxes; segmented buttons for departure-time ranges; a paste box with example chips and a status message (`role="status"`) for found, partial and no-history results.

## Map

- MapLibre with a muted, low-contrast basemap, so the routes carry the color.
- Curved great-circle-style route lines through each hub; the selected itinerary's route is thicker and solid, the others thin and dashed. Selection is never shown by color alone.
- Airport and hub labels in text; hubs drawn as outlined circles.
- The basemap provider's attribution is always visible (constitution, data licences).

## Interaction and motion

- Selection is kept in the URL ([ADR-0010](adr/0010-url-selection-state.md)), so every view can be linked.
- Transitions are short (150–250 ms) and functional only; with `prefers-reduced-motion`, there is no motion.
- Loading shows the layout's shape, not spinners over empty space; missing data says "insufficient data" or "no history", never a placeholder number.

## Accessibility

- WCAG 2.2 AA as the floor: the contrast above; touch targets at least 44 px; visible focus (3 px accent outline).
- Real `button`, `a`, `input`, `select` and `label` elements throughout; tabs use `role="tablist"`/`role="tab"`; status messages use `role="status"`.
- Every chart has a text equivalent (an `aria-label` listing the values, or the values printed beside it).
- Every interaction works by keyboard; automated checks are axe-core plus scripted keyboard tests (constitution, Principle II).

## Wording

- "Connection feasibility" in methodology text; "worked on X% of days" in the interface.
- Always the period and sample: "of 314 days, Jul 2024 – Jun 2025".
- No passenger-outcome language ("passengers missed", "chance of making"); the report's forbidden-wording list applies to the interface too.
- Suggestions state their evidence: "60 min shorter; worked on 97% vs 95% of days (difference −1 to +5 points, 95% CI)".
