import asyncio
from bot.services.database import get_all_study_plan_groups, get_study_plans_by_group

async def check():
    groups = await get_all_study_plan_groups()
    print(f"المجموعات: {len(groups)}")
    for g in groups:
        plans = await get_study_plans_by_group(g.id)
        print(f"\n{g.id}. {g.title} (tag: {g.group_tag}) - {len(plans)} خطط")
        for p in plans:
            print(f"   - {p.title}")

asyncio.run(check())
