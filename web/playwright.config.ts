// Browser tests (research R6). All projects except `smoke` run against the production build
// served locally, with every request outside that server blocked (FR-022). Screenshots are
// compared only inside the pinned Playwright container, so they match on every machine.
import { defineConfig, devices } from "@playwright/test";

const inDocker = process.env.PLAYWRIGHT_DOCKER === "1";
const smokeUrl = process.env.SMOKE_URL;

export default defineConfig({
  testDir: "tests",
  outputDir: "test-results",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  ...(process.env.CI ? { workers: 2 } : {}),
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  snapshotPathTemplate: "{testDir}/visual/__screenshots__/{arg}-{projectName}{ext}",
  expect: {
    toHaveScreenshot: { maxDiffPixels: 0, animations: "disabled", caret: "hide" },
  },
  use: {
    baseURL: smokeUrl ?? "http://127.0.0.1:4173/",
    trace: "retain-on-failure",
    reducedMotion: "reduce",
    locale: "en-US",
    timezoneId: "UTC",
  },
  ...(smokeUrl
    ? {}
    : {
        webServer: {
          command: "npx vite preview --host 127.0.0.1 --port 4173 --strictPort",
          url: "http://127.0.0.1:4173/",
          reuseExistingServer: !process.env.CI,
          timeout: 60_000,
        },
      }),
  projects: [
    {
      name: "e2e",
      testMatch: "e2e/**/*.spec.ts",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "visual",
      testMatch: "visual/**/*.spec.ts",
      // Refuses to run outside the pinned container (contracts/checks.md).
      testIgnore: inDocker ? [] : ["**/*"],
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "a11y",
      testMatch: "a11y/**/*.spec.ts",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "keyboard",
      testMatch: "keyboard/**/*.spec.ts",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "smoke",
      testMatch: "smoke/**/*.spec.ts",
      testIgnore: smokeUrl ? [] : ["**/*"],
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
