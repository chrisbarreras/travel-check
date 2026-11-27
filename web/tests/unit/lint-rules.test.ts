// Data may be loaded only inside src/data/ (FR-011; contracts/data-access.md, Enforcement).
import { ESLint } from "eslint";
import tseslint from "typescript-eslint";
import { describe, expect, it } from "vitest";

// Vitest runs from web/.
const root = process.cwd();

async function ruleIds(code: string, filePath: string): Promise<string[]> {
  // The snippets are not files in the TypeScript project, so type-aware rules are off here;
  // the data-access rules under test are not type-aware.
  const eslint = new ESLint({ cwd: root, overrideConfig: tseslint.configs.disableTypeChecked });
  const [result] = await eslint.lintText(code, { filePath });
  return (result?.messages ?? []).map((m) => m.ruleId ?? "");
}

describe("data-access lint rules", () => {
  it("forbid fetch and site-data imports in components", async () => {
    const ids = await ruleIds(
      'import data from "../../../site-data/showcase/index.json";\n' +
        'export const load = () => fetch("/data/showcase/index.json").then(() => data);\n',
      "src/components/Bad.tsx",
    );
    expect(ids).toContain("no-restricted-globals");
    expect(ids).toContain("no-restricted-imports");
  });

  it("forbid window.fetch too", async () => {
    const ids = await ruleIds(
      'export const load = () => window.fetch("/x");\n',
      "src/components/Bad.tsx",
    );
    expect(ids).toContain("no-restricted-properties");
  });

  it("allow fetch inside src/data/", async () => {
    const ids = await ruleIds(
      'export const load = () => fetch("/data/showcase/index.json");\n',
      "src/data/loader.ts",
    );
    expect(ids).not.toContain("no-restricted-globals");
  });
}, 60_000);
