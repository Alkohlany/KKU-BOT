import asyncio
import asyncpg
import httpx

BOT_TOKEN = None  # Will read from env

async def main():
    # Read bot token from .env
    global BOT_TOKEN
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('BOT_TOKEN='):
                BOT_TOKEN = line.strip().split('=', 1)[1]
                break
    
    if not BOT_TOKEN:
        print("BOT_TOKEN not found in .env")
        return
    
    print(f"BOT_TOKEN: {BOT_TOKEN[:10]}...")
    
    conn = await asyncpg.connect('postgresql://kku_bot_user:DufoC9U0OtShdvhQ8qkIi29mfF6UrqF0@dpg-d955u9vavr4c739vcrqg-a.oregon-postgres.render.com/kku_bot')
    
    rows = await conn.fetch('SELECT * FROM channel_groups')
    
    async with httpx.AsyncClient() as client:
        for row in rows:
            chat_id = row['chat_id']
            title = row['title']
            
            # Get member count
            member_count = 0
            try:
                resp = await client.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={chat_id}')
                data = resp.json()
                if data.get('ok'):
                    member_count = data['result']
                    print(f"Got member count for {title}: {member_count}")
            except Exception as e:
                print(f"Error getting member count for {title}: {e}")
            
            # Get invite link
            invite_link = None
            try:
                resp = await client.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getChat?chat_id={chat_id}')
                data = resp.json()
                if data.get('ok'):
                    invite_link = data['result'].get('invite_link')
                    print(f"Got invite link for {title}: {invite_link}")
            except Exception as e:
                print(f"Error getting chat info for {title}: {e}")
            
            # Update database
            await conn.execute(
                'UPDATE channel_groups SET member_count = $1, invite_link = $2 WHERE id = $3',
                member_count, invite_link, row['id']
            )
            print(f"Updated {title}: members={member_count}, link={invite_link}")
    
    await conn.close()
    print("\nDone!")

asyncio.run(main())
