// Fails when the data the first view loads, or any route file, is above its budget
// (specs/003 SC-002; specs/004 FR-017).
import { readdirSync, readFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { fileURLToPath } from "node:url";

const BUDGET_KB = 150;
const dir = fileURLToPath(new URL("../dist/data/showcase/", import.meta.url));
const gz = (file) => gzipSync(readFileSync(dir + file), { level: 9 }).length / 1024;

const index = JSON.parse(readFileSync(dir + "index.json", "utf8"));
const landingRoute = index.routes.find((r) => r.route_id === index.landing.route_id);
// The default view: the index, manifest and landing comparison, then the landing route's file.
const firstView = ["index.json", "manifest.json", "landing.json", landingRoute.file];

let failed = false;
let total = 0;
for (const file of firstView) {
  const size = gz(file);
  total += size;
  console.log(`  ${file}: ${size.toFixed(1)} KB gzip`);
}
console.log(
  `check-data-size: first-view data ${total.toFixed(1)} KB gzip (budget ${String(BUDGET_KB)} KB)`,
);
if (total > BUDGET_KB) failed = true;

const routes = readdirSync(dir + "routes").map((f) => [f, gz(`routes/${f}`)]);
const [largest, largestKb] = routes.sort((a, b) => b[1] - a[1])[0];
console.log(
  `check-data-size: largest route file ${largest} ${largestKb.toFixed(1)} KB gzip (budget ${String(BUDGET_KB)} KB)`,
);
if (largestKb > BUDGET_KB) failed = true;

if (failed) process.exit(1);
