
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://neraca:neraca@localhost:5432/neraca"
)

pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, open=False)


def init_pool() -> None:
    pool.open(wait=True, timeout=30)


def close_pool() -> None:
    pool.close()


@contextmanager
def get_conn() -> Iterator:
    with pool.connection() as conn:
        conn.row_factory = dict_row
        yield conn


def ping() -> bool:
    """Dipakai endpoint /api/health untuk membuktikan API <-> DB hidup."""
    with get_conn() as conn:
        return conn.execute("SELECT 1 AS ok").fetchone()["ok"] == 1
