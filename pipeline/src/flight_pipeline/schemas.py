"""JSON Schema and TypeScript types for the published showcase shapes (specs/002 research
R6, FR-012, ADR-0007).

The Pydantic models in ``flight_pipeline.showcase.models`` are the single definition. Their
JSON Schema goes to ``shared/schemas/showcase.schema.json``; TypeScript types are generated
from that schema with the pinned ``json-schema-to-typescript`` through ``npx`` into
``shared/types/showcase.ts``. Both are committed; ``schemas --check`` regenerates them and
reports any difference (CI fails on it).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from pydantic.json_schema import GenerateJsonSchema, models_json_schema

from flight_pipeline.showcase.models import PUBLISHED_MODELS

GENERATOR = "json-schema-to-typescript@15.0.4"
SCHEMA_PATH = "shared/schemas/showcase.schema.json"
TYPES_PATH = "shared/types/showcase.ts"
BANNER = (
    "/* Generated from shared/schemas/showcase.schema.json by "
    f"{GENERATOR} (`flight-pipeline schemas`). Do not edit. */"
)

TypesGenerator = Callable[[bytes], bytes]


class SchemaError(RuntimeError):
    """The generator could not run. Exit code 1."""


class _NoFieldTitles(GenerateJsonSchema):
    """Model titles only: field titles would make the TypeScript generator emit one alias
    type per field (``CiLow``, ``CiLow1``, ...) instead of inline types."""

    def field_title_should_be_set(self, schema: Any) -> bool:
        return False


def json_schema() -> dict[str, Any]:
    """One schema whose definitions cover every published model."""
    _, schema = models_json_schema(
        [(m, "serialization") for m in PUBLISHED_MODELS],
        title="Showcase",
        schema_generator=_NoFieldTitles,
    )
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["description"] = (
        "Published showcase files (specs/002-showcase-data-pipeline contracts/outputs.md). "
        "Generated from flight_pipeline.showcase.models; do not edit."
    )
    return schema


def schema_bytes() -> bytes:
    return (json.dumps(json_schema(), indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def npx_generator(schema: bytes) -> bytes:
    """Run the pinned json-schema-to-typescript on ``schema`` and return LF-normalized
    TypeScript."""
    npx = shutil.which("npx")
    if npx is None:
        raise SchemaError("npx not found: install Node.js 20 or later to generate types")
    with tempfile.TemporaryDirectory(prefix="flight-schemas-") as tmp:
        src = Path(tmp) / "showcase.schema.json"
        out = Path(tmp) / "showcase.ts"
        src.write_bytes(schema)
        cmd = [
            npx,
            "--yes",
            GENERATOR,
            "--input",
            str(src),
            "--output",
            str(out),
            "--unreachableDefinitions",
            "--no-additionalProperties",
            "--bannerComment",
            BANNER,
        ]
        done = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if done.returncode != 0 or not out.exists():
            raise SchemaError(f"{GENERATOR} failed: {done.stderr.strip() or done.stdout.strip()}")
        text = out.read_text(encoding="utf-8").replace("\r\n", "\n")
    return text.encode("utf-8")


def generate(generator: TypesGenerator = npx_generator) -> dict[str, bytes]:
    """The files to commit, by path relative to the repository root."""
    schema = schema_bytes()
    return {SCHEMA_PATH: schema, TYPES_PATH: generator(schema)}


def write(root: Path, files: Mapping[str, bytes]) -> None:
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def differences(root: Path, files: Mapping[str, bytes]) -> list[str]:
    """Committed files that are missing or differ from a fresh generation."""
    out: list[str] = []
    for name, data in sorted(files.items()):
        path = root / name
        if not path.exists():
            out.append(f"{name} is missing")
        elif path.read_bytes() != data:
            out.append(f"{name} differs from a fresh generation")
    return out
