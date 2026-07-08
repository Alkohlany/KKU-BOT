import asyncio
import asyncpg
import sys
sys.stdout.reconfigure(encoding='utf-8')

async def main():
    conn = await asyncpg.connect('postgresql://kku_bot_user:DufoC9U0OtShdvhQ8qkIi29mfF6UrqF0@dpg-d955u9vavr4c739vcrqg-a.oregon-postgres.render.com/kku_bot')
    
    rows = await conn.fetch('SELECT id, LEFT(content, 80) as content_preview, target_channels, is_published, publish_to_channel, group_message_ids, schedule_time, created_at FROM scheduled_posts ORDER BY id DESC LIMIT 5')
    
    for r in rows:
        print(f"ID: {r['id']}")
        print(f"Content: {r['content_preview']}")
        print(f"target_channels: {repr(r['target_channels'])}")
        print(f"is_published: {r['is_published']}")
        print(f"publish_to_channel: {r['publish_to_channel']}")
        print(f"group_message_ids: {r['group_message_ids']}")
        print(f"schedule_time: {r['schedule_time']}")
        print(f"created_at: {r['created_at']}")
        print("---")
    
    await conn.close()

asyncio.run(main())
