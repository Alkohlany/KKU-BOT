import asyncio
import asyncpg
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

async def main():
    conn = await asyncpg.connect(
        "postgresql://kku_bot_user:DufoC9U0OtShdvhQ8qkIi29mfF6UrqF0@dpg-d955u9vavr4c739vcrqg-a.oregon-postgres.render.com/kku_bot"
    )
    count = await conn.fetchval("SELECT count(*) FROM scheduled_posts")
    print(f"Total rows: {count}")
    print()
    rows = await conn.fetch("SELECT id, target_channels, is_published, publish_to_channel, group_message_ids, schedule_time, created_at FROM scheduled_posts ORDER BY id")
    for r in rows:
        print(f"id={r['id']} | target_channels={r['target_channels']} | is_pub={r['is_published']} | pub_to_ch={r['publish_to_channel']} | group_msg_ids={r['group_message_ids']} | sched={r['schedule_time']} | created={r['created_at']}")
    await conn.close()

asyncio.run(main())
