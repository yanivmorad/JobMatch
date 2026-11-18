import os
from urllib.parse import urlparse

import asyncpg
import pytest

TEST_DSN = os.getenv("TEST_DATABASE_URL")


def _assert_disposable(dsn: str):
    """הגנה: הבדיקות מוחקות את כל הסכמה, לכן מותר רק DB ששמו מכיל 'test'."""
    db_name = urlparse(dsn).path.lstrip("/")
    if "test" not in db_name.lower():
        raise RuntimeError(
            f"TEST_DATABASE_URL must point to a disposable DB whose name contains 'test' (got '{db_name}')"
        )


@pytest.fixture
async def empty_db(monkeypatch):
    """
    DB ריק לגמרי (DROP SCHEMA public) + pool חדש שמצביע עליו.
    מדלג אם לא הוגדר TEST_DATABASE_URL.
    """
    if not TEST_DSN:
        pytest.skip("TEST_DATABASE_URL not set")
    _assert_disposable(TEST_DSN)

    conn = await asyncpg.connect(TEST_DSN)
    try:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    finally:
        await conn.close()

    from db import postgres

    monkeypatch.setenv("DATABASE_URL", TEST_DSN)
    await postgres.close_pool()
    yield TEST_DSN
    await postgres.close_pool()


@pytest.fixture
async def db(empty_db):
    """DB עם סכמה מוכנה."""
    from db.postgres import get_pool

    await get_pool()
    yield empty_db


@pytest.fixture
async def raw_conn(empty_db):
    """חיבור ישיר לבדיקות (מחוץ ל-pool של האפליקציה)."""
    conn = await asyncpg.connect(empty_db)
    yield conn
    await conn.close()
