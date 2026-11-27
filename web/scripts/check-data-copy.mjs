// Fails when the built site's showcase files differ from the committed ones (FR-016).
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const source = fileURLToPath(new URL("../../site-data/showcase/", import.meta.url));
const built = fileURLToPath(new URL("../dist/data/showcase/", import.meta.url));

function files(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
}
const sha = (path) => createHash("sha256").update(readFileSync(path)).digest("hex");

const problems = [];
const sourceFiles = files(source).map((p) => relative(source, p));
for (const file of sourceFiles) {
  try {
    if (sha(join(source, file)) !== sha(join(built, file))) problems.push(`${file}: differs`);
  } catch {
    problems.push(`${file}: missing from dist/data/showcase/`);
  }
}
const extra = files(built)
  .map((p) => relative(built, p))
  .filter((f) => !sourceFiles.includes(f));
for (const file of extra) problems.push(`${file}: not in site-data/showcase/`);

if (problems.length > 0) {
  console.error(`check-data-copy: ${problems.length} problem(s)\n  ${problems.join("\n  ")}`);
  process.exit(1);
}
console.log(`check-data-copy: ${sourceFiles.length} files identical to site-data/showcase/`);
