import shutil
import os
import sys
import asyncio

sys.stdout.reconfigure(encoding='utf-8')
from bot.services.database import async_session
from bot.models.models import StudyPlanGroup, StudyPlan

source_dir = r"C:\Users\qqq\Downloads\Telegram Desktop"
dest_dir = r"C:\Users\qqq\Desktop\KKU BOT\kku-bot\uploads"

groups_data = [
    {
        "title": "خطط التخصصات لكلية اللغات والترجمة",
        "description": "خطط تخصصات كلية اللغات والترجمة",
        "group_tag": "لغات",
        "plans": [
            ("خطة الترجمة", "خطة الترجمة.pdf"),
            ("خطة اللغة الإنجليزية", "خطة اللغة الإنجليزية.pdf"),
        ]
    },
    {
        "title": "🟢محدث خطط التخصصات 1447هـ",
        "description": "خطط تخصصات كلية الثقافة والفنون",
        "group_tag": "فنون",
        "plans": [
            ("خطة العلوم الموسيقية", "العلوم الموسيقية .pdf"),
            ("خطة المسرح والفنون الأدائية", "المسرح والفنون الأدائية .pdf"),
            ("خطة الفنون السينمائية", "الفنون السينمائية .pdf"),
        ]
    },
    {
        "title": "🟢محدث خطط التخصصات 1447هـ",
        "description": "خطط تخصصات كلية السياحة",
        "group_tag": "سياحه",
        "plans": [
            ("خطة فنون الطهي", "فنون الطهي.pdf"),
            ("خطة إدارة الضيافة الدولية", "إدارة الضيافة الدولية .pdf"),
            ("خطة إدارة الوجهات السياحية الدولية", "إدارة الوجهات السياحية الدولية .pdf"),
        ]
    }
]

async def main():
    for group in groups_data:
        for title, filename in group["plans"]:
            src = os.path.join(source_dir, filename)
            dst = os.path.join(dest_dir, filename)
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
                print(f"copied: {filename}")

    async with async_session() as session:
        for group in groups_data:
            new_group = StudyPlanGroup(
                title=group["title"],
                description=group["description"],
                group_tag=group["group_tag"],
                is_active=True
            )
            session.add(new_group)
            await session.commit()
            await session.refresh(new_group)

            for title, filename in group["plans"]:
                plan = StudyPlan(
                    group_id=new_group.id,
                    title=title,
                    plan_url=os.path.join(dest_dir, filename),
                    is_active=True
                )
                session.add(plan)

            await session.commit()
            print(f"added: {group['group_tag']} - {len(group['plans'])} plans")

asyncio.run(main())
