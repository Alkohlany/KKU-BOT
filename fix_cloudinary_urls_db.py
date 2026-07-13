import asyncio
import asyncpg

DB_URL = "postgresql://kku_bot_user:DufoC9U0OtShdvhQ8qkIi29mfF6UrqF0@dpg-d955u9vavr4c739vcrqg-a.oregon-postgres.render.com/kku_bot"

async def main():
    conn = await asyncpg.connect(DB_URL)
    r1 = await conn.execute("UPDATE auto_responses SET file_url = NULL WHERE file_url LIKE '%cloudinary%'")
    r2 = await conn.execute("UPDATE news SET file_url = NULL WHERE file_url LIKE '%cloudinary%'")
    print(f"auto_responses: {r1}")
    print(f"news: {r2}")
    await conn.close()

asyncio.run(main())
