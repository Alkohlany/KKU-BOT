import asyncio
from bot.services.database import async_session
from bot.models.models import StudyPlanGroup, StudyPlan
from sqlalchemy import select, delete

async def delete_duplicate():
    async with async_session() as session:
        # حذف الخطط المرتبطة بالمجموعة 5
        stmt = delete(StudyPlan).where(StudyPlan.group_id == 5)
        await session.execute(stmt)
        
        # حذف المجموعة 5
        stmt = delete(StudyPlanGroup).where(StudyPlanGroup.id == 5)
        await session.execute(stmt)
        
        await session.commit()
        print("deleted group 5")

asyncio.run(delete_duplicate())
