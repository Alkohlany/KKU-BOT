import asyncio
import asyncpg

DB_URL = "postgresql://kku_bot_user:DufoC9U0OtShdvhQ8qkIi29mfF6UrqF0@dpg-d955u9vavr4c739vcrqg-a.oregon-postgres.render.com/kku_bot"

async def main():
    conn = await asyncpg.connect(DB_URL)
    rows = await conn.fetch("SELECT id, file_url FROM auto_responses WHERE file_url IS NOT NULL")
    for r in rows:
        print(f"auto_responses id={r['id']}: {r['file_url']}")
    
    rows = await conn.fetch("SELECT id, image_url, file_url, thumbnail_url, files_json FROM news WHERE image_url IS NOT NULL OR file_url IS NOT NULL OR thumbnail_url IS NOT NULL")
    for r in rows:
        print(f"news id={r['id']}: image={r['image_url']}, file={r['file_url']}, thumb={r['thumbnail_url']}, json={r['files_json'][:100] if r['files_json'] else None}")

    rows = await conn.fetch("SELECT id, file_url FROM questions WHERE file_url IS NOT NULL")
    for r in rows:
        print(f"questions id={r['id']}: {r['file_url']}")

    rows = await conn.fetch("SELECT id, image_url, file_url, thumbnail_url, files_json FROM scheduled_posts WHERE image_url IS NOT NULL OR file_url IS NOT NULL")
    for r in rows:
        print(f"scheduled_posts id={r['id']}: image={r['image_url']}, file={r['file_url']}")

    rows = await conn.fetch("SELECT id, plan_url, file_url FROM study_plans WHERE plan_url IS NOT NULL OR file_url IS NOT NULL")
    for r in rows:
        print(f"study_plans id={r['id']}: plan_url={r['plan_url']}, file_url={r['file_url']}")

    await conn.close()

asyncio.run(main())
