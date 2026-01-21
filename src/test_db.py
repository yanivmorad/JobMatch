# test_db.py
import asyncio

from db.postgres import get_pool


async def test():
    pool = await get_pool()
    print("Success! Database initialized and pool created.")
    # בדוק אם אפשר להריץ שאילתה
    async with pool.acquire() as conn:
        res = await conn.fetch("SELECT * FROM jobs")
        print(f"Jobs in DB: {len(res)}")


if __name__ == "__main__":
    asyncio.run(test())
