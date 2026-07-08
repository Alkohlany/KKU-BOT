import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://kku_bot_user:DufoC9U0OtShdvhQ8qkIi29mfF6UrqF0@dpg-d955u9vavr4c739vcrqg-a.oregon-postgres.render.com/kku_bot')
    
    rows = await conn.fetch('SELECT * FROM channel_groups ORDER BY id')
    print('=== channel_groups ===')
    for row in rows:
        print(dict(row))
    
    cols = await conn.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'channel_groups'")
    print('\n=== columns ===')
    for col in cols:
        print(dict(col))
    
    # Check if the group has correct chat_id
    print('\n=== chat_id check ===')
    for row in rows:
        print(f"ID: {row['id']}, chat_id: {row['chat_id']} (type: {type(row['chat_id'])}), title: {row['title']}, type: {row['type']}, member_count: {row['member_count']}")
    
    await conn.close()

asyncio.run(main())
