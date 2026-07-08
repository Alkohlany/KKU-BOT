import asyncio
import asyncpg

DB_URL = "postgresql://kku_bot_user:DufoC9U0OtShdvhQ8qkIi29mfF6UrqF0@dpg-d955u9vavr4c739vcrqg-a.oregon-postgres.render.com/kku_bot"

async def main():
    conn = await asyncpg.connect(DB_URL)

    # --- scheduled_posts ---
    print("=" * 80)
    print("SCHEDULED POSTS TABLE")
    print("=" * 80)

    rows = await conn.fetch("SELECT * FROM scheduled_posts ORDER BY id")
    print("Total rows:", len(rows))
    print()

    if rows:
        cols = list(rows[0].keys())
        print("Columns:", ", ".join(cols))
        print()

        for row in rows:
            print("-" * 60)
            for col in cols:
                val = row[col]
                if col == "content" and isinstance(val, str) and len(val) > 100:
                    val = val[:100] + "..."
                print("  " + str(col) + ": " + str(val))
        print("-" * 60)
    else:
        print("  (no rows found)")

    # --- channel_groups ---
    print()
    print("=" * 80)
    print("CHANNEL_GROUPS TABLE")
    print("=" * 80)

    rows2 = await conn.fetch("SELECT * FROM channel_groups ORDER BY id")
    print("Total rows:", len(rows2))
    print()

    if rows2:
        cols2 = list(rows2[0].keys())
        print("Columns:", ", ".join(cols2))
        print()

        for row in rows2:
            print("-" * 60)
            for col in cols2:
                print("  " + str(col) + ": " + str(row[col]))
        print("-" * 60)
    else:
        print("  (no rows found)")

    await conn.close()

asyncio.run(main())
