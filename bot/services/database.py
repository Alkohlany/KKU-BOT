from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.models.models import Base, User, Group, AutoResponse, BannedUser, ActivityLog, News, Question, ScheduledPost, StudyPlan, StudyPlanGroup, ResponseCategory, Settings
from bot.config import DATABASE_URL
from sqlalchemy import select, update, delete, func, text
from datetime import datetime, timezone, timedelta
import logging
import os

logger = logging.getLogger(__name__)

pool_settings = {
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

if "sqlite" in DATABASE_URL:
    pool_settings = {}

engine = create_async_engine(DATABASE_URL, echo=False, **pool_settings)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")

        await conn.execute(text("ALTER TABLE study_plans ADD COLUMN IF NOT EXISTS channel_message_id INTEGER"))
        await conn.execute(text("ALTER TABLE study_plans ADD COLUMN IF NOT EXISTS group_id INTEGER REFERENCES study_plan_groups(id)"))
        await conn.execute(text("ALTER TABLE study_plan_groups ADD COLUMN IF NOT EXISTS channel_message_id INTEGER"))

        result = await conn.execute(select(StudyPlan).limit(1))
        if not result.scalar_one_or_none():
            for plan_data in [
                ("خطة بكالوريوس هندسة الحاسب", "برنامج دراسي لدرجة البكالوريوس في هندسة الحاسب والمعلومات، يشمل البرمجة وشبكات الحاسب والذكاء الاصطناعي", "كلية الهندسة", "بكالوريوس"),
                ("خطة بكالوريوس إدارة الأعمال", "برنامج دراسي لدرجة البكالوريوس في إدارة الأعمال، يشمل التسويق والمالية وإدارة الموارد البشرية", "كلية إدارة الأعمال", "بكالوريوس"),
                ("خطة بكالوريوس الطب البشري", "برنامج دراسي لدرجة بكالوريوس الطب البشري، مدة 7 سنوات تشمل مرحلة العلوم الطبية والتمريض والتدريب السريري", "كلية الطب", "بكالوريوس"),
                ("خطة بكالوريوس التربية", "برنامج دراسي لدرجة البكالوريوس في التربية، يشمل أساليب التدريس وعلم النفس التربوي والمناهج", "كلية التربية", "بكالوريوس"),
            ]:
                await conn.execute(
                    text("INSERT INTO study_plans (title, description, faculty, level, is_active, created_at) VALUES (:title, :description, :faculty, :level, true, NOW())"),
                    {"title": plan_data[0], "description": plan_data[1], "faculty": plan_data[2], "level": plan_data[3]}
                )
            logger.info("Seeded 4 test study plans")


async def get_user(telegram_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def create_user(telegram_id: int, username: str = None, first_name: str = None) -> User:
    async with async_session() as session:
        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def update_user_subscription(telegram_id: int, is_subscribed: bool):
    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(is_subscribed=is_subscribed, last_check=datetime.utcnow())
        )
        await session.commit()


async def add_group(chat_id: int, title: str = None) -> Group:
    async with async_session() as session:
        group = Group(chat_id=chat_id, title=title)
        session.add(group)
        await session.commit()
        await session.refresh(group)
        return group


async def get_group(chat_id: int) -> Group | None:
    async with async_session() as session:
        result = await session.execute(
            select(Group).where(Group.chat_id == chat_id)
        )
        return result.scalar_one_or_none()


async def get_all_groups():
    async with async_session() as session:
        result = await session.execute(select(Group))
        return result.scalars().all()


async def get_all_active_groups():
    async with async_session() as session:
        result = await session.execute(select(Group).where(Group.is_active == True))
        return result.scalars().all()


async def remove_group(chat_id: int):
    async with async_session() as session:
        await session.execute(
            delete(Group).where(Group.chat_id == chat_id)
        )
        await session.commit()


async def add_auto_response(keyword: str, response: str, created_by: int) -> AutoResponse:
    async with async_session() as session:
        ar = AutoResponse(keyword=keyword, response=response, created_by=created_by)
        session.add(ar)
        await session.commit()
        await session.refresh(ar)
        return ar


async def get_auto_responses() -> list[AutoResponse]:
    async with async_session() as session:
        result = await session.execute(
            select(AutoResponse).where(AutoResponse.is_active == True)
        )
        return list(result.scalars().all())


async def get_all_auto_responses() -> list[AutoResponse]:
    async with async_session() as session:
        result = await session.execute(select(AutoResponse))
        return list(result.scalars().all())


async def remove_auto_response(response_id: int):
    async with async_session() as session:
        await session.execute(
            delete(AutoResponse).where(AutoResponse.id == response_id)
        )
        await session.commit()


async def ban_user(telegram_id: int, reason: str = None, banned_by: int = None) -> BannedUser:
    async with async_session() as session:
        ban = BannedUser(telegram_id=telegram_id, reason=reason, banned_by=banned_by)
        session.add(ban)
        await session.commit()
        await session.refresh(ban)
        return ban


async def is_banned(telegram_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(BannedUser).where(BannedUser.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none() is not None


async def log_activity(action: str, details: str = None, performed_by: int = None):
    async with async_session() as session:
        log = ActivityLog(action=action, details=details, performed_by=performed_by)
        session.add(log)
        await session.commit()


# ==================== News ====================
async def add_news(title, content, image_url=None, file_url=None, created_by=None):
    async with async_session() as session:
        news = News(title=title, content=content, image_url=image_url, 
                   file_url=file_url, created_by=created_by)
        session.add(news)
        await session.commit()
        return news

async def get_all_news():
    async with async_session() as session:
        result = await session.execute(select(News).order_by(News.created_at.desc()))
        return result.scalars().all()

async def publish_news(news_id):
    async with async_session() as session:
        await session.execute(
            update(News).where(News.id == news_id).values(is_published=True, published_at=func.now())
        )
        await session.commit()

async def delete_news(news_id):
    async with async_session() as session:
        await session.execute(delete(News).where(News.id == news_id))
        await session.commit()


# ==================== Questions ====================
async def add_question(question, answer, category=None, keywords=None):
    async with async_session() as session:
        q = Question(question=question, answer=answer, category=category, keywords=keywords)
        session.add(q)
        await session.commit()
        return q

async def get_all_questions():
    async with async_session() as session:
        result = await session.execute(select(Question).where(Question.is_active == True))
        return result.scalars().all()

async def search_question(text):
    async with async_session() as session:
        result = await session.execute(
            select(Question).where(
                Question.is_active == True,
                (Question.keywords.ilike(f"%{text}%")) | (Question.question.ilike(f"%{text}%"))
            )
        )
        question = result.scalars().first()
        if question:
            return question

        words = text.split()
        if len(words) > 1:
            from sqlalchemy import or_
            conditions = []
            for word in words:
                if len(word) > 2:
                    conditions.append(Question.keywords.ilike(f"%{word}%"))
                    conditions.append(Question.question.ilike(f"%{word}%"))
            if conditions:
                result = await session.execute(
                    select(Question).where(
                        Question.is_active == True,
                        or_(*conditions)
                    ).limit(1)
                )
                return result.scalars().first()
        return None

async def increment_question_usage(question_id):
    async with async_session() as session:
        await session.execute(
            update(Question).where(Question.id == question_id).values(usage_count=Question.usage_count + 1)
        )
        await session.commit()

async def delete_question(question_id):
    async with async_session() as session:
        await session.execute(delete(Question).where(Question.id == question_id))
        await session.commit()


# ==================== Scheduled Posts ====================
async def add_scheduled_post(title, content, schedule_time, image_url=None, file_url=None, 
                            is_recurring=False, recurring_interval=None, created_by=None):
    async with async_session() as session:
        post = ScheduledPost(title=title, content=content, schedule_time=schedule_time,
                            image_url=image_url, file_url=file_url, is_recurring=is_recurring,
                            recurring_interval=recurring_interval, created_by=created_by)
        session.add(post)
        await session.commit()
        return post

async def get_pending_posts():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with async_session() as session:
        result = await session.execute(
            select(ScheduledPost).where(
                ScheduledPost.is_published == False,
                ScheduledPost.schedule_time <= now
            )
        )
        return result.scalars().all()

async def get_all_scheduled_posts():
    async with async_session() as session:
        result = await session.execute(select(ScheduledPost).order_by(ScheduledPost.schedule_time.desc()))
        return result.scalars().all()

async def mark_post_published(post_id):
    async with async_session() as session:
        await session.execute(
            update(ScheduledPost).where(ScheduledPost.id == post_id).values(is_published=True, published_at=func.now())
        )
        await session.commit()

async def reschedule_post(post_id: int, recurring_interval: str):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if recurring_interval == "daily":
        next_time = now + timedelta(days=1)
    elif recurring_interval == "weekly":
        next_time = now + timedelta(weeks=1)
    elif recurring_interval == "monthly":
        next_time = now + timedelta(days=30)
    else:
        next_time = now + timedelta(days=1)

    async with async_session() as session:
        await session.execute(
            update(ScheduledPost).where(ScheduledPost.id == post_id).values(
                is_published=False,
                schedule_time=next_time,
                published_at=None
            )
        )
        await session.commit()

async def delete_scheduled_post(post_id):
    async with async_session() as session:
        await session.execute(delete(ScheduledPost).where(ScheduledPost.id == post_id))
        await session.commit()


# ==================== Study Plan Groups ====================
async def get_all_study_plan_groups():
    async with async_session() as session:
        result = await session.execute(
            select(StudyPlanGroup).where(StudyPlanGroup.is_active == True)
        )
        return result.scalars().all()

async def get_study_plan_group_by_id(group_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(StudyPlanGroup).where(StudyPlanGroup.id == group_id)
        )
        return result.scalar_one_or_none()

async def create_study_plan_group(title: str, description: str = None, group_tag: str = None):
    async with async_session() as session:
        group = StudyPlanGroup(title=title, description=description, group_tag=group_tag)
        session.add(group)
        await session.commit()
        await session.refresh(group)
        return group

async def update_study_plan_group(group_id: int, title: str = None, description: str = None, group_tag: str = None, channel_message_id: int = None):
    async with async_session() as session:
        stmt = select(StudyPlanGroup).where(StudyPlanGroup.id == group_id)
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()
        if not group:
            return None
        if title is not None:
            group.title = title
        if description is not None:
            group.description = description
        if group_tag is not None:
            group.group_tag = group_tag
        if channel_message_id is not None:
            group.channel_message_id = channel_message_id
        await session.commit()
        await session.refresh(group)
        return group

async def delete_study_plan_group(group_id: int):
    async with async_session() as session:
        plans_stmt = select(StudyPlan).where(StudyPlan.group_id == group_id)
        plans_result = await session.execute(plans_stmt)
        plans = plans_result.scalars().all()
        for plan in plans:
            await session.delete(plan)

        stmt = select(StudyPlanGroup).where(StudyPlanGroup.id == group_id)
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()

        if group:
            await session.delete(group)
            await session.commit()
            return True
        return False


# ==================== Study Plans ====================
async def add_study_plan(title, description, faculty, level, plan_url=None, file_url=None, group_id=None):
    async with async_session() as session:
        plan = StudyPlan(title=title, description=description, faculty=faculty,
                        level=level, plan_url=plan_url, file_url=file_url, group_id=group_id)
        session.add(plan)
        await session.commit()
        return plan

async def get_all_study_plans():
    async with async_session() as session:
        result = await session.execute(select(StudyPlan).where(StudyPlan.is_active == True))
        return result.scalars().all()

async def get_study_plans_by_group(group_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(StudyPlan).where(StudyPlan.is_active == True, StudyPlan.group_id == group_id)
        )
        return result.scalars().all()

async def get_study_plan_by_id(plan_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(StudyPlan).where(StudyPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

async def get_study_plans_by_faculty(faculty):
    async with async_session() as session:
        result = await session.execute(
            select(StudyPlan).where(StudyPlan.is_active == True, StudyPlan.faculty == faculty)
        )
        return result.scalars().all()

async def update_study_plan(plan_id, title=None, description=None, faculty=None, level=None, plan_url=None):
    async with async_session() as session:
        stmt = select(StudyPlan).where(StudyPlan.id == plan_id)
        result = await session.execute(stmt)
        plan = result.scalar_one_or_none()

        if not plan:
            return None

        if title is not None:
            plan.title = title
        if description is not None:
            plan.description = description
        if faculty is not None:
            plan.faculty = faculty
        if level is not None:
            plan.level = level
        if plan_url is not None:
            plan.plan_url = plan_url

        await session.commit()
        await session.refresh(plan)
        return plan

def _normalize_arabic(text: str) -> str:
    return text.replace("ة", "ه").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


async def search_study_plans(query):
    async with async_session() as session:
        stmt = select(StudyPlan).where(
            StudyPlan.is_active == True
        )
        result = await session.execute(stmt)
        plans = result.scalars().all()

        query_norm = _normalize_arabic(query.lower())
        words = [w for w in query_norm.split() if len(w) > 1]

        found = []
        for plan in plans:
            searchable = _normalize_arabic(" ".join(filter(None, [
                plan.title or "",
                plan.faculty or "",
                plan.description or ""
            ])).lower())

            if query_norm in searchable:
                found.append(plan)
            elif words and any(w in searchable for w in words):
                found.append(plan)

        return found


async def delete_study_plan(plan_id):
    async with async_session() as session:
        await session.execute(delete(StudyPlan).where(StudyPlan.id == plan_id))
        await session.commit()


# ==================== Response Categories ====================
async def add_response_category(name, description=None, icon=None, order=0):
    async with async_session() as session:
        cat = ResponseCategory(name=name, description=description, icon=icon, order=order)
        session.add(cat)
        await session.commit()
        return cat

async def get_all_categories():
    async with async_session() as session:
        result = await session.execute(select(ResponseCategory).order_by(ResponseCategory.order))
        return result.scalars().all()

async def delete_response_category(cat_id):
    async with async_session() as session:
        await session.execute(delete(ResponseCategory).where(ResponseCategory.id == cat_id))
        await session.commit()
