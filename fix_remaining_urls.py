import os
import asyncio
import asyncpg


async def main():
    database_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(database_url)

    try:
        rows = await conn.fetch(
            "SELECT id, file_url FROM study_plans WHERE file_url LIKE '%25%'"
        )
        print(f"Found {len(rows)} study_plans with double-encoded URLs\n")

        fixed = 0
        for row in rows:
            fixed_url = row["file_url"].replace("%25", "%")
            if fixed_url == row["file_url"]:
                continue
            await conn.execute(
                "UPDATE study_plans SET file_url = $1 WHERE id = $2",
                fixed_url,
                row["id"],
            )
            print(f"  [{row['id']}] Fixed: {row['file_url'][:80]}...")
            print(f"       -> {fixed_url[:80]}...")
            fixed += 1

        print(f"\nDone. Fixed {fixed} URLs.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
