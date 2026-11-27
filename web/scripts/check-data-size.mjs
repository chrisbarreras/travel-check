// Fails when the data the first view loads is above its budget (SC-002).
import { readFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { fileURLToPath } from "node:url";

const BUDGET_KB = 150;
const FIRST_VIEW = ["index.json", "landing.json", "manifest.json"];
const dir = fileURLToPath(new URL("../dist/data/showcase/", import.meta.url));

let total = 0;
for (const file of FIRST_VIEW) {
  const size = gzipSync(readFileSync(dir + file), { level: 9 }).length;
  total += size;
  console.log(`  ${file}: ${(size / 1024).toFixed(1)} KB gzip`);
}
const totalKb = total / 1024;
console.log(
  `check-data-size: first-view data ${totalKb.toFixed(1)} KB gzip (budget ${String(BUDGET_KB)} KB)`,
);
if (totalKb > BUDGET_KB) process.exit(1);
