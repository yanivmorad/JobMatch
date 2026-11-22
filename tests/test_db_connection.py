"""הגדרות החיבור ל-DB בענן (Neon): בלי חיבור אמיתי."""
from db import postgres


def test_neon_channel_binding_is_dropped(monkeypatch):
    """מחרוזת החיבור של Neon כוללת channel_binding=require - asyncpg היה שולח אותה לשרת כהגדרה לא מוכרת."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://u:p@ep-cool-1.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
    )
    kwargs = postgres._connect_kwargs()
    assert kwargs["dsn"] == "postgresql://u:p@ep-cool-1.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    assert "statement_cache_size" not in kwargs


def test_neon_pooler_disables_the_statement_cache(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@ep-cool-1-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require")
    assert postgres._connect_kwargs()["statement_cache_size"] == 0


def test_pool_is_small_and_recycles_idle_connections(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.delenv("DB_POOL_MAX", raising=False)
    kwargs = postgres._connect_kwargs()
    assert kwargs["min_size"] == 1 and kwargs["max_size"] == 5
    # Neon נרדם אחרי 5 דקות וסוגר חיבורים - חיבור רדום מוחלף לפני כן
    assert kwargs["max_inactive_connection_lifetime"] < 300


def test_pg_vars_still_work_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PG_HOST", "db.local")
    monkeypatch.setenv("PG_PORT", "5433")
    kwargs = postgres._connect_kwargs()
    assert kwargs["host"] == "db.local" and kwargs["port"] == 5433 and kwargs["min_size"] == 1
