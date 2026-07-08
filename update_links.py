import asyncio
import asyncpg
import httpx

async def main():
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('BOT_TOKEN='):
                BOT_TOKEN = line.strip().split('=', 1)[1]
                break
    
    conn = await asyncpg.connect('postgresql://kku_bot_user:DufoC9U0OtShdvhQ8qkIi29mfF6UrqF0@dpg-d955u9vavr4c739vcrqg-a.oregon-postgres.render.com/kku_bot')
    
    rows = await conn.fetch('SELECT * FROM channel_groups')
    
    async with httpx.AsyncClient() as client:
        for row in rows:
            chat_id = row['chat_id']
            title = row['title']
            
            # Get chat info
            try:
                resp = await client.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getChat?chat_id={chat_id}')
                data = resp.json()
                if data.get('ok'):
                    chat_info = data['result']
                    username = chat_info.get('username')
                    if username:
                        link = f"https://t.me/{username}"
                    else:
                        link = chat_info.get('invite_link')
                    
                    # Update database
                    await conn.execute(
                        'UPDATE channel_groups SET invite_link = $1 WHERE id = $2',
                        link, row['id']
                    )
                    print(f"Updated {title}: {link}")
            except Exception as e:
                print(f"Error for {title}: {e}")
    
    await conn.close()
    print("\nDone!")

asyncio.run(main())
