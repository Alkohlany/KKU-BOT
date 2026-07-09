import asyncio
import os
import sys
from dotenv import load_dotenv
import asyncpg
import httpx

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def publish_all():
    conn = await asyncpg.connect(DATABASE_URL)

    groups = await conn.fetch("SELECT id, title, description, group_tag, channel_message_id FROM study_plan_groups ORDER BY id")
    print(f"Found {len(groups)} groups\n")

    channel_row = await conn.fetchrow("SELECT chat_id, invite_link FROM channel_groups WHERE type = 'channel' AND is_active = true ORDER BY created_at DESC LIMIT 1")
    CHANNEL_ID = str(channel_row["chat_id"]) if channel_row else None
    CHANNEL_USERNAME = None
    if channel_row:
        invite_link = channel_row.get("invite_link")
        if invite_link and 't.me/' in invite_link:
            CHANNEL_USERNAME = invite_link.split('t.me/')[-1].strip('/')
    if not CHANNEL_USERNAME and CHANNEL_ID:
        CHANNEL_USERNAME = CHANNEL_ID

    if not CHANNEL_ID:
        print("No active channel found in database, aborting")
        return

    for group in groups:
        gid = group["id"]
        title = group["title"]
        tag = group["group_tag"] or ""
        channel_msg_id = group["channel_message_id"]
        print(f"=== Group {gid}: {title} ===")

        plans = await conn.fetch(
            "SELECT id, title, file_url, channel_message_id FROM study_plans WHERE group_id = $1 AND is_active = true ORDER BY id",
            gid
        )

        unpublished = [p for p in plans if p["channel_message_id"] is None]
        print(f"  {len(plans)} total, {len(unpublished)} unpublished")

        if not unpublished and not channel_msg_id:
            print("  No unpublished plans and no group post, skipping")
            print()
            continue

        published_count = 0
        async with httpx.AsyncClient() as client:
            for plan in unpublished:
                caption = f"#{tag}\n" if tag else ""
                caption += f"تخصص - {plan['title']}\n"
                caption += f"\n🔴انظموا لقروب جامعة الملك خالد العام\n\nhttps://t.me/KKU_Main1 \n\n\nانظمو لقروب الواتساب العام\n\nhttps://whatsapp.com/channel/0029VbD8NhHC1FuKSEmrJY2W"

                try:
                    if plan["file_url"]:
                        file_resp = await client.get(plan["file_url"], timeout=60)
                        if file_resp.status_code == 200:
                            files = {"document": ("plan.pdf", file_resp.content, "application/pdf")}
                            data = {"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}
                            resp = await client.post(
                                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                                files=files,
                                data=data,
                                timeout=60
                            )
                        else:
                            data = {"chat_id": CHANNEL_ID, "text": caption + f"\n\n📎 {plan['file_url']}", "parse_mode": "HTML"}
                            resp = await client.post(
                                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                data=data,
                                timeout=30
                            )
                    else:
                        data = {"chat_id": CHANNEL_ID, "text": caption, "parse_mode": "HTML"}
                        resp = await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                            data=data,
                            timeout=30
                        )

                    if resp.status_code == 200:
                        result = resp.json()
                        if result.get("ok"):
                            msg_id = result["result"]["message_id"]
                            await conn.execute(
                                "UPDATE study_plans SET channel_message_id = $1 WHERE id = $2",
                                msg_id, plan["id"]
                            )
                            print(f"  ✅ Published plan {plan['id']}: {plan['title']} -> msg {msg_id}")
                        else:
                            print(f"  ❌ API error for plan {plan['id']}: {result}")
                    else:
                        print(f"  ❌ HTTP {resp.status_code} for plan {plan['id']}")
                except Exception as e:
                    print(f"  ❌ Error publishing plan {plan['id']}: {e}")

                await asyncio.sleep(1)

        if channel_msg_id:
            channel_username = CHANNEL_USERNAME
            all_plans = await conn.fetch(
                "SELECT title, channel_message_id FROM study_plans WHERE group_id = $1 AND is_active = true ORDER BY id",
                gid
            )

            text = f"📂 {title}\n"
            if group["description"]:
                text += f"{group['description']}\n"
            text += "\n"

            for p in all_plans:
                if p["channel_message_id"]:
                    plan_link = f"https://t.me/{channel_username}/{p['channel_message_id']}"
                    text += f"{p['title']} ⬇️\n{plan_link}\n\n"
                else:
                    text += f"{p['title']}\n\n"

            text += "\n🔴انظموا لقروب جامعة الملك خالد العام\n\nhttps://t.me/KKU_Main1 \n\n\nانظمو لقروب الواتساب العام\n\nhttps://whatsapp.com/channel/0029VbD8NhHC1FuKSEmrJY2W\n\n#شاركها_فربما_يبحث_عنها_غيرك"

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
                    data={
                        "chat_id": CHANNEL_ID,
                        "message_id": channel_msg_id,
                        "text": text,
                        "parse_mode": "HTML"
                    },
                    timeout=30
                )
                if resp.status_code == 200 and resp.json().get("ok"):
                    print(f"  ✅ Updated group post {channel_msg_id}")
                else:
                    print(f"  ❌ Failed to update group post: {resp.status_code} {resp.text[:100]}")
        else:
            channel_username = CHANNEL_USERNAME
            text = f"📂 {title}\n"
            if group["description"]:
                text += f"{group['description']}\n"
            text += "\n"

            all_plans = await conn.fetch(
                "SELECT title, channel_message_id FROM study_plans WHERE group_id = $1 AND is_active = true ORDER BY id",
                gid
            )
            for p in all_plans:
                if p["channel_message_id"]:
                    plan_link = f"https://t.me/{channel_username}/{p['channel_message_id']}"
                    text += f"{p['title']} ⬇️\n{plan_link}\n\n"
                else:
                    text += f"{p['title']}\n\n"

            text += "\n🔴انظموا لقروب جامعة الملك خالد العام\n\nhttps://t.me/KKU_Main1 \n\n\nانظمو لقروب الواتساب العام\n\nhttps://whatsapp.com/channel/0029VbD8NhHC1FuKSEmrJY2W\n\n#شاركها_فربما_يبحث_عنها_غيرك"

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    data={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"},
                    timeout=30
                )
                if resp.status_code == 200 and resp.json().get("ok"):
                    msg_id = resp.json()["result"]["message_id"]
                    await conn.execute(
                        "UPDATE study_plan_groups SET channel_message_id = $1 WHERE id = $2",
                        msg_id, gid
                    )
                    print(f"  ✅ Created group post: msg {msg_id}")
                else:
                    print(f"  ❌ Failed to create group post: {resp.status_code}")

        print()

    await conn.close()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(publish_all())
