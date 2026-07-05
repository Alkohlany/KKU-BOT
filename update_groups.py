import asyncio
from bot.services.database import async_session
from bot.models.models import StudyPlanGroup
from sqlalchemy import select

updates = {
    2: "🟢خطط التخصصات الصحية 1447هـ",
    3: "💻خطط كلية علوم الحاسب والمعلومات 1447هـ",
    4: "📜برامج الدبلوم 1447هـ",
    5: "🔬خطط كلية العلوم 1447هـ",
    6: "☪️خطط كلية الشريعة والدراسات الإسلامية 1447هـ",
    7: "🏗️خطط كلية الهندسة 1447هـ",
    8: "📚خطط كلية التربية 1447هـ",
    9: "💼خطط كلية الأعمال 1447هـ",
    10: "📖خطط كلية العلوم الإنسانية 1447هـ",
    11: "🌐خطط كلية اللغات والترجمة 1447هـ",
    12: "🎨خطط كلية الثقافة والفنون 1447هـ",
    13: "✈️خطط كلية السياحة 1447هـ",
}

async def update_names():
    async with async_session() as session:
        for group_id, new_title in updates.items():
            stmt = select(StudyPlanGroup).where(StudyPlanGroup.id == group_id)
            result = await session.execute(stmt)
            group = result.scalar_one_or_none()
            
            if group:
                group.title = new_title
                print(f"updated: {group_id} -> {new_title}")
            else:
                print(f"not found: {group_id}")
        
        await session.commit()
        print("\ndone!")

asyncio.run(update_names())
