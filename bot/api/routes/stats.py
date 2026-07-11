from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from bot.services.database import get_db
from bot.api.auth import get_current_user
from bot.models.models import User, ChannelGroup, AutoResponse, BannedUser, ActivityLog, Settings

router = APIRouter()

DAY_NAMES = {
    6: "السبت",
    0: "الأحد",
    1: "الاثنين",
    2: "الثلاثاء",
    3: "الأربعاء",
    4: "الخميس",
    5: "الجمعة",
}


@router.get("")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    groups_count = (await db.execute(select(func.count(ChannelGroup.id)))).scalar() or 0
    responses_count = (await db.execute(select(func.count(AutoResponse.id)))).scalar() or 0
    banned_count = (await db.execute(select(func.count(BannedUser.id)))).scalar() or 0

    return {
        "users": users_count,
        "groups": groups_count,
        "responses": responses_count,
        "banned": banned_count,
    }


@router.get("/weekly")
async def get_weekly_stats(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    today = datetime.utcnow().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    result = await db.execute(
        select(
            func.date(ActivityLog.created_at).label("day"),
            func.count(ActivityLog.id).label("count"),
        )
        .where(ActivityLog.created_at >= datetime.combine(week_start, datetime.min.time()))
        .where(ActivityLog.created_at <= datetime.combine(week_end, datetime.max.time()))
        .group_by(func.date(ActivityLog.created_at))
        .order_by(func.date(ActivityLog.created_at))
    )
    rows = result.all()

    counts_by_day = {}
    for row in rows:
        day_date = row.day
        if isinstance(day_date, str):
            day_date = datetime.strptime(day_date, "%Y-%m-%d").date()
        counts_by_day[day_date.weekday()] = row.count

    data = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_num = day.weekday()
        data.append({
            "name": DAY_NAMES.get(day_num, str(day_num)),
            "رسائل": counts_by_day.get(day_num, 0),
        })

    return {"data": data}


@router.get("/activity")
async def get_activity(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(50)
    )
    items = result.scalars().all()
    return [
        {
            "id": a.id,
            "type": a.action or "system",
            "text": a.details or "",
            "time": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
            "user": str(a.performed_by) if a.performed_by else "system",
        }
        for a in items
    ]


@router.get("/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Settings))
    settings_list = result.scalars().all()

    settings = {}
    for s in settings_list:
        settings[s.key] = s.value

    defaults = {
        "welcomeMessage": "مرحباً بك في مجموعة الجامعة! 👋",
        "requireSubscription": "true",
        "autoGreeting": "true",
        "linkFilter": "false",
        "ai_fallback_enabled": "true",
        "antiSpam": "true",
        "antiFlood": "true",
        "floodLimit": "5",
        "floodTime": "60",
        "botLanguage": "ar",
    }

    for key, default in defaults.items():
        if key not in settings:
            settings[key] = default

    return settings


@router.put("/settings")
async def update_settings(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    for key, value in data.items():
        stmt = select(Settings).where(Settings.key == key)
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = str(value)
        else:
            setting = Settings(key=key, value=str(value))
            db.add(setting)

    await db.commit()
    return {"message": "Settings updated successfully"}
