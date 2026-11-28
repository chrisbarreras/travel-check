// Runs the browser tests inside the pinned Playwright image, as CI does (research R6;
// contracts/checks.md). `test` runs every browser project; `update` rewrites the visual
// reference images, which then go through review in the pull request.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export const IMAGE =
  "mcr.microsoft.com/playwright:v1.65.0-noble@sha256:9beb546099e11f52d62e505537914870e01a67e0e6b00ae41da4775324e73dbe";

const mode = process.argv[2];
if (mode !== "test" && mode !== "update") {
  console.error("usage: node scripts/docker-playwright.mjs test|update");
  process.exit(2);
}

const repo = fileURLToPath(new URL("../../", import.meta.url));
const projects = "--project=e2e --project=visual --project=a11y --project=keyboard";
const playwright =
  mode === "update"
    ? "npx playwright test --project=visual --update-snapshots"
    : `npx playwright test ${projects}`;

// node_modules lives in a Docker volume, so Linux packages never mix with the host's.
const script = ["npm ci --no-audit --no-fund", "npm run build", playwright].join(" && ");
const args = [
  "run",
  "--rm",
  "--ipc=host",
  "--init",
  "-e",
  "CI=1",
  "-e",
  "PLAYWRIGHT_DOCKER=1",
  "-v",
  `${repo}:/work`,
  "-v",
  "travel-check-web-node-modules:/work/web/node_modules",
  "-w",
  "/work/web",
  IMAGE,
  "bash",
  "-c",
  script,
];

const result = spawnSync("docker", args, { stdio: "inherit" });
process.exit(result.status ?? 1);
