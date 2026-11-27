// Checks loaded data against the generated contract (FR-012; research R3).
import type { RouteFile, ShowcaseIndex, ShowcaseManifest } from "@contract";
import {
  type Validator,
  validateRouteFile,
  validateShowcaseIndex,
  validateShowcaseManifest,
} from "./generated/validators.js";
import type { Result } from "./types";

function check<T>(validator: Validator, file: string, data: unknown): Result<T> {
  if (validator(data)) return { ok: true, value: data as T };
  const first = validator.errors?.[0];
  const detail = first
    ? `${first.instancePath || "/"} ${first.message ?? "is invalid"}`
    : "does not match the data contract";
  return { ok: false, error: { kind: "invalid", file, detail } };
}

export const checkIndex = (file: string, data: unknown): Result<ShowcaseIndex> =>
  check(validateShowcaseIndex, file, data);

export const checkRouteFile = (file: string, data: unknown): Result<RouteFile> =>
  check(validateRouteFile, file, data);

export const checkManifest = (file: string, data: unknown): Result<ShowcaseManifest> =>
  check(validateShowcaseManifest, file, data);
