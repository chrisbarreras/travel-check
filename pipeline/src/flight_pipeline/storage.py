"""Deterministic Parquet output (research R8).

Every table is written with an explicit sort order, fixed writer settings and floating-point
columns rounded to 6 decimals, then validated against its Pydantic model.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Collection, Sequence
from pathlib import Path
from typing import Any, TypeVar

import duckdb
from pydantic import BaseModel

from flight_pipeline.models import (
    _as_utc,  # pyright: ignore[reportPrivateUsage]
    _datetime_fields,  # pyright: ignore[reportPrivateUsage]
    validate_table,
)

M = TypeVar("M", bound=BaseModel)

FLOAT_DECIMALS = 6
_FLOAT_TYPES = {"DOUBLE", "FLOAT", "REAL", "DECIMAL"}


THREADS_ENV = "FLIGHT_PIPELINE_THREADS"


def worker_count() -> int:
    """Threads or worker processes to use: ``FLIGHT_PIPELINE_THREADS`` when set, else the
    machine's CPU count."""
    threads = os.environ.get(THREADS_ENV)
    return max(1, int(threads)) if threads else max(1, os.cpu_count() or 1)


def connect() -> duckdb.DuckDBPyConnection:
    """An in-memory DuckDB connection in UTC. ``FLIGHT_PIPELINE_THREADS`` limits its threads
    (to time a run as on a smaller machine, SC-008); outputs never depend on it."""
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    con.execute("SET preserve_insertion_order = true")
    threads = os.environ.get(THREADS_ENV)
    if threads:
        con.execute(f"SET threads = {int(threads)}")
    return con


def _quote_path(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def write_table(
    con: duckdb.DuckDBPyConnection,
    table: str,
    path: Path,
    model: type[BaseModel],
    order_by: Sequence[str],
) -> int:
    """Validate ``table`` against ``model`` and write it to ``path`` sorted by ``order_by``.
    Returns the row count."""
    rows = validate_table(con, table, model)
    described = con.execute(f"DESCRIBE {table}").fetchall()
    cols: list[str] = []
    for row in described:
        name, col_type = str(row[0]), str(row[1])
        q = f'"{name}"'
        if col_type.split("(")[0].upper() in _FLOAT_TYPES:
            cols.append(f"round({q}, {FLOAT_DECIMALS}) AS {q}")
        else:
            cols.append(q)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".parquet.part")
    order = ", ".join(_order_term(c) for c in order_by)
    con.execute(
        f"COPY (SELECT {', '.join(cols)} FROM {table} ORDER BY {order}) TO {_quote_path(part)} "
        "(FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 122880)"
    )
    part.replace(path)
    return rows


def _order_term(term: str) -> str:
    """``"name"`` or ``"name DESC"`` -> quoted SQL ORDER BY term."""
    name, _, direction = term.partition(" ")
    direction = direction.strip().upper()
    if direction not in ("", "ASC", "DESC"):
        raise ValueError(f"bad sort term {term!r}")
    return f'"{name}" {direction}'.strip()


def read_models[M: BaseModel](
    con: duckdb.DuckDBPyConnection,
    path: Path,
    model: type[M],
    *,
    only: tuple[str, Collection[str]] | None = None,
) -> list[M]:
    """Load a Parquet table as validated model instances (naive timestamps read as UTC), in
    file order. With ``only=(column, values)``, just the rows whose ``column`` is one of
    ``values`` (filtered before validation, for large tables)."""
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; run the earlier pipeline stages first")
    source = f"SELECT * FROM read_parquet({_quote_path(path)})"
    if only is not None:
        column, values = only
        con.execute("CREATE OR REPLACE TEMP TABLE _only_keys (k VARCHAR PRIMARY KEY)")
        if values:
            con.executemany("INSERT INTO _only_keys VALUES (?)", [[v] for v in sorted(values)])
        source = (
            f"SELECT * FROM read_parquet({_quote_path(path)}, file_row_number = true) "
            f'WHERE "{column}" IN (SELECT k FROM _only_keys) ORDER BY file_row_number'
        )
        source = f"SELECT * EXCLUDE (file_row_number) FROM ({source})"
    cur = con.execute(source)
    columns = [d[0] for d in cur.description or []]
    dt_fields = _datetime_fields(model)
    out: list[M] = []
    for row in cur.fetchall():
        rec = dict(zip(columns, row, strict=True))
        for name in dt_fields:
            rec[name] = _as_utc(rec[name])
        out.append(model.model_validate(rec))
    return out


def read_table(con: duckdb.DuckDBPyConnection, path: Path, table: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; run the earlier pipeline stages first")
    con.execute(
        f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_parquet({_quote_path(path)})"
    )


def table_hash(con: duckdb.DuckDBPyConnection, path: Path) -> str:
    """SHA-256 of a Parquet file's rows in file order, independent of file metadata."""
    h = hashlib.sha256()
    cur = con.execute(f"SELECT * FROM read_parquet({_quote_path(path)})")
    while batch := cur.fetchmany(50_000):
        for row in batch:
            h.update(repr(row).encode())
            h.update(b"\n")
    return h.hexdigest()


# --- Models -> typed DuckDB tables --------------------------------------------------------

_SCALARS: dict[type, str] = {
    bool: "BOOLEAN",
    int: "BIGINT",
    float: "DOUBLE",
    str: "VARCHAR",
}


def duck_type(annotation: Any) -> str:
    """DuckDB column type for a model field annotation (nullable types map to their base)."""
    import datetime as dt
    import types
    import typing

    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is typing.Annotated:
        return duck_type(args[0])
    if origin in (typing.Union, types.UnionType):
        non_null = [a for a in args if a is not type(None)]
        if len(non_null) == 1:
            return duck_type(non_null[0])
        if all(typing.get_origin(a) is typing.Literal for a in non_null):
            return "VARCHAR"
        return duck_type(non_null[0])
    if origin is typing.Literal:
        return "VARCHAR"
    if origin is list:
        return f"{duck_type(args[0])}[]"
    if origin is dict:
        return f"MAP({duck_type(args[0])}, {duck_type(args[1])})"
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        fields = ", ".join(
            f'"{n}" {duck_type(f.annotation)}' for n, f in annotation.model_fields.items()
        )
        return f"STRUCT({fields})"
    if annotation is dt.datetime:
        return "TIMESTAMP"
    if annotation is dt.date:
        return "DATE"
    if isinstance(annotation, type) and annotation in _SCALARS:
        return _SCALARS[annotation]
    if "datetime" in repr(annotation).lower():
        return "TIMESTAMP"
    raise TypeError(f"no DuckDB type for {annotation!r}")


def _plain(value: Any) -> Any:
    import datetime as dt

    if isinstance(value, BaseModel):
        return {k: _plain(v) for k, v in value}
    if isinstance(value, list):
        return [_plain(v) for v in value]  # pyright: ignore[reportUnknownVariableType]
    if isinstance(value, dt.datetime) and value.tzinfo is not None:
        return value.astimezone(dt.UTC).replace(tzinfo=None)  # storage convention: naive UTC
    return value


def models_to_table(
    con: duckdb.DuckDBPyConnection,
    table: str,
    model: type[BaseModel],
    items: Sequence[BaseModel],
) -> None:
    """Create ``table`` with one typed column per field of ``model`` and insert ``items``."""
    cols = ", ".join(f'"{n}" {duck_type(f.annotation)}' for n, f in model.model_fields.items())
    con.execute(f"CREATE OR REPLACE TABLE {table} ({cols})")
    names = list(model.model_fields)
    row = "(" + ", ".join("?" for _ in names) + ")"
    # Multi-row INSERTs: executemany runs one statement per row, far slower on large tables.
    for start in range(0, len(items), _INSERT_BATCH):
        batch = items[start : start + _INSERT_BATCH]
        con.execute(
            f"INSERT INTO {table} VALUES " + ", ".join(row for _ in batch),
            [_plain(getattr(item, n)) for item in batch for n in names],
        )


_INSERT_BATCH = 500
