// Smoke check of a deployed site: `npm run smoke -- <url>` (FR-025). The only check that uses
// the network; it is not part of the test suite.
import { spawnSync } from "node:child_process";

const url = process.argv[2];
if (!url || !/^https:\/\//.test(url)) {
  console.error("usage: npm run smoke -- https://<deployed site>/");
  process.exit(2);
}
const result = spawnSync("npx", ["playwright", "test", "--project=smoke"], {
  stdio: "inherit",
  shell: process.platform === "win32",
  env: { ...process.env, SMOKE_URL: url.endsWith("/") ? url : `${url}/` },
});
process.exit(result.status ?? 1);
