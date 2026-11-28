import { screen, within } from "@testing-library/react";

/** Waits for the landing comparison and returns queries scoped to it. */
export async function landingRegion() {
  const region = await screen.findByRole("region", { name: /^The example:/ });
  return { region, ...within(region) };
}
