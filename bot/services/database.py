from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.models.models import Base, User, ChannelGroup, AutoResponse, BannedUser, ActivityLog, News, Question, ScheduledPost, StudyPlan, StudyPlanGroup, BookGroup, Book, Settings, SpamPattern, QueryCache
from bot.config import DATABASE_URL
from sqlalchemy import select, update, delete, func, text
from datetime import datetime, timezone, timedelta
import logging
import os
from bot.config import normalize_arabic

logger = logging.getLogger(__name__)

pool_settings = {
    "pool_size": 5,
    "max_overflow": 5,
    "pool_timeout": 30,
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

if "sqlite" in DATABASE_URL:
    pool_settings = {}

engine = create_async_engine(DATABASE_URL, echo=False, **pool_settings)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def update_fields(obj, **kwargs):
    for key, value in kwargs.items():
        if value is not None and hasattr(obj, key):
            setattr(obj, key, value)


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def run_migrations():
    """Create indexes if they don't exist."""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_auto_responses_news_id ON auto_responses (news_id)",
        "CREATE INDEX IF NOT EXISTS idx_auto_responses_source_chat_id ON auto_responses (source_chat_id)",
        "CREATE INDEX IF NOT EXISTS idx_auto_responses_source_message_id ON auto_responses (source_message_id)",
        "CREATE INDEX IF NOT EXISTS idx_questions_news_id ON questions (news_id)",
        "CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log (created_at)",
        "CREATE INDEX IF NOT EXISTS idx_activity_log_action ON activity_log (action)",
        "CREATE INDEX IF NOT EXISTS idx_scheduled_posts_is_published ON scheduled_posts (is_published)",
        "CREATE INDEX IF NOT EXISTS idx_scheduled_posts_schedule_time ON scheduled_posts (schedule_time)",
        "CREATE INDEX IF NOT EXISTS idx_study_plans_group_id ON study_plans (group_id)",
    ]
    async with engine.begin() as conn:
        for sql in indexes:
            await conn.execute(text(sql))
    logger.info("Database indexes created successfully")


async def add_missing_columns():
    """Add columns that may be missing from older auto_responses tables."""
    columns = [
        "ALTER TABLE auto_responses ADD COLUMN IF NOT EXISTS file_tg_id VARCHAR(200)",
        "ALTER TABLE auto_responses ADD COLUMN IF NOT EXISTS source_chat_id BIGINT",
        "ALTER TABLE auto_responses ADD COLUMN IF NOT EXISTS source_message_id INTEGER",
        "ALTER TABLE auto_responses ADD COLUMN IF NOT EXISTS news_id INTEGER",
    ]
    create_tables = [
        """CREATE TABLE IF NOT EXISTS query_cache (
            id INTEGER PRIMARY KEY,
            query TEXT NOT NULL,
            normalized_query TEXT NOT NULL,
            response_title TEXT NOT NULL,
            response_link VARCHAR(500),
            response_text TEXT,
            hit_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]
    async with engine.begin() as conn:
        for sql in columns:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass
        for sql in create_tables:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass


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


async def add_auto_response(keyword: str, response: str, created_by: int, file_url: str = None, file_type: str = None, as_document: bool = False, news_id: int = None) -> AutoResponse:
    async with async_session() as session:
        ar = AutoResponse(keyword=keyword, response=response, created_by=created_by, file_url=file_url, file_type=file_type, as_document=as_document, news_id=news_id)
        session.add(ar)
        await session.commit()
        await session.refresh(ar)
        return ar


async def get_setting(key: str) -> str:
    async with async_session() as session:
        result = await session.execute(select(Settings.value).where(Settings.key == key))
        row = result.scalar_one_or_none()
        return row


async def get_auto_responses() -> list[AutoResponse]:
    """إرجاع الردود الفعالة بترتيب ثابت، الأحدث أولاً."""
    async with async_session() as session:
        result = await session.execute(
            select(AutoResponse)
            .where(AutoResponse.is_active == True)
            .order_by(AutoResponse.created_at.desc(), AutoResponse.id.desc())
        )
        return list(result.scalars().all())


async def get_auto_response_by_id(response_id: int) -> AutoResponse | None:
    async with async_session() as session:
        result = await session.execute(select(AutoResponse).where(AutoResponse.id == response_id))
        return result.scalar_one_or_none()


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


async def get_auto_responses_by_source(chat_id: int, message_id: int) -> list[AutoResponse]:
    async with async_session() as session:
        result = await session.execute(
            select(AutoResponse).where(
                AutoResponse.source_chat_id == chat_id,
                AutoResponse.source_message_id == message_id
            )
        )
        return list(result.scalars().all())


async def remove_auto_responses_by_source(chat_id: int, message_id: int):
    async with async_session() as session:
        await session.execute(
            delete(AutoResponse).where(
                AutoResponse.source_chat_id == chat_id,
                AutoResponse.source_message_id == message_id
            )
        )
        await session.commit()


async def update_auto_response(response_id: int, keyword: str = None, response: str = None, is_active: bool = None, file_url: str = None, file_type: str = None, as_document: bool = None, news_id: int = None):
    async with async_session() as session:
        ar = (await session.execute(select(AutoResponse).where(AutoResponse.id == response_id))).scalar_one_or_none()
        if not ar:
            return None
        update_fields(ar, keyword=keyword, response=response, is_active=is_active, file_url=file_url, file_type=file_type, as_document=as_document, news_id=news_id)
        await session.commit()
        await session.refresh(ar)
        return ar


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


async def get_all_banned():
    async with async_session() as session:
        result = await session.execute(select(BannedUser))
        return list(result.scalars().all())


async def log_activity(action: str, details: str = None, performed_by: int = None):
    async with async_session() as session:
        log = ActivityLog(action=action, details=details, performed_by=performed_by)
        session.add(log)
        await session.commit()


# ==================== News ====================
async def add_news(content, image_url=None, file_url=None, thumbnail_url=None, file_name=None, file_type=None, created_by=None, as_document=False, file_id=None, target_channels=None, files_json=None):
    async with async_session() as session:
        news = News(content=content, image_url=image_url, 
                   file_url=file_url, thumbnail_url=thumbnail_url, file_name=file_name, file_type=file_type, created_by=created_by,
                   as_document=as_document, file_id=file_id, target_channels=target_channels, files_json=files_json)
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
        # Delete related AutoResponse and Question records first
        await session.execute(delete(AutoResponse).where(AutoResponse.news_id == news_id))
        await session.execute(delete(Question).where(Question.news_id == news_id))
        # Now delete the news
        await session.execute(delete(News).where(News.id == news_id))
        await session.commit()

async def get_news_by_id(news_id: int):
    async with async_session() as session:
        result = await session.execute(select(News).where(News.id == news_id))
        return result.scalar_one_or_none()

async def update_news(news_id, content=None, image_url=None, file_url=None, as_document=None, channel_message_id=None, group_message_ids=None, target_channels=None, is_published=None, file_name=None, file_type=None, thumbnail_url=None, files_json=None):
    async with async_session() as session:
        news = (await session.execute(select(News).where(News.id == news_id))).scalar_one_or_none()
        if not news:
            return None
        update_fields(news, content=content, image_url=image_url, file_url=file_url, as_document=as_document, channel_message_id=channel_message_id, group_message_ids=group_message_ids, target_channels=target_channels, is_published=is_published, file_name=file_name, file_type=file_type, thumbnail_url=thumbnail_url, files_json=files_json)
        await session.commit()
        return news

async def delete_all_news():
    async with async_session() as session:
        # Delete related records first
        await session.execute(delete(AutoResponse))
        await session.execute(delete(Question))
        await session.execute(delete(News))
        await session.commit()

async def get_news_by_channel_message_id(channel_message_id):
    async with async_session() as session:
        result = await session.execute(select(News).where(News.channel_message_id == channel_message_id))
        return result.scalar_one_or_none()

async def get_news_by_group_message_id(chat_id, message_id):
    import json as _json
    async with async_session() as session:
        result = await session.execute(select(News))
        for news in result.scalars().all():
            if news.group_message_ids:
                try:
                    ids = _json.loads(news.group_message_ids)
                    if str(chat_id) in ids and ids[str(chat_id)] == message_id:
                        return news
                except Exception:
                    pass
    return None


# ==================== Questions ====================
async def add_question(question, answer, category=None, keywords=None, file_url=None, file_type=None, as_document=False, news_id=None):
    async with async_session() as session:
        q = Question(question=question, answer=answer, category=category, keywords=keywords, file_url=file_url, file_type=file_type, as_document=as_document, news_id=news_id)
        session.add(q)
        await session.commit()
        await session.refresh(q)
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

async def update_question(question_id: int, question: str = None, answer: str = None, category: str = None, keywords: str = None, file_url: str = None, file_type: str = None, as_document: bool = None):
    async with async_session() as session:
        q = (await session.execute(select(Question).where(Question.id == question_id))).scalar_one_or_none()
        if not q:
            return None
        update_fields(q, question=question, answer=answer, category=category, keywords=keywords, file_url=file_url, file_type=file_type, as_document=as_document)
        await session.commit()
        await session.refresh(q)
        return q


# ==================== Scheduled Posts ====================
async def add_scheduled_post(content, schedule_time, image_url=None, file_url=None, 
                            is_recurring=False, recurring_interval=None, created_by=None,
                            as_document=False, target_channels=None, title=None,
                            file_name=None, file_type=None, file_id=None, thumbnail_url=None,
                            files_json=None):
    async with async_session() as session:
        post = ScheduledPost(content=content, schedule_time=schedule_time,
                            image_url=image_url, file_url=file_url, is_recurring=is_recurring,
                            recurring_interval=recurring_interval, created_by=created_by,
                            as_document=as_document, target_channels=target_channels,
                            file_name=file_name, file_type=file_type, file_id=file_id, thumbnail_url=thumbnail_url,
                            files_json=files_json)
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

async def mark_post_published(post_id, group_message_ids=None):
    async with async_session() as session:
        update_data = {
            "is_published": True,
            "published_at": func.now()
        }
        if group_message_ids:
            update_data["group_message_ids"] = group_message_ids
        await session.execute(
            update(ScheduledPost)
            .where(ScheduledPost.id == post_id)
            .values(**update_data)
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

async def get_scheduled_post(post_id):
    async with async_session() as session:
        result = await session.execute(select(ScheduledPost).where(ScheduledPost.id == post_id))
        return result.scalar_one_or_none()

async def update_scheduled_post(post_id, **kwargs):
    async with async_session() as session:
        result = await session.execute(select(ScheduledPost).where(ScheduledPost.id == post_id))
        post = result.scalar_one_or_none()
        if post:
            for key, value in kwargs.items():
                if value is not None:
                    setattr(post, key, value)
            await session.commit()
            await session.refresh(post)
        return post

async def delete_all_scheduled_posts():
    async with async_session() as session:
        await session.execute(text("DELETE FROM scheduled_posts"))
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
        group = (await session.execute(select(StudyPlanGroup).where(StudyPlanGroup.id == group_id))).scalar_one_or_none()
        if not group:
            return None
        update_fields(group, title=title, description=description, group_tag=group_tag, channel_message_id=channel_message_id)
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
async def add_study_plan(title, description=None, faculty=None, level=None, plan_url=None, file_url=None, group_id=None, specialization=None, link=None):
    async with async_session() as session:
        plan = StudyPlan(title=title, description=description, faculty=faculty,
                        level=level, plan_url=plan_url, file_url=file_url, group_id=group_id,
                        specialization=specialization, link=link)
        session.add(plan)
        await session.commit()
        await session.refresh(plan)
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

async def update_study_plan(plan_id, title=None, description=None, faculty=None, level=None, plan_url=None, specialization=None, link=None):
    async with async_session() as session:
        plan = (await session.execute(select(StudyPlan).where(StudyPlan.id == plan_id))).scalar_one_or_none()
        if not plan:
            return None
        update_fields(plan, title=title, description=description, faculty=faculty, level=level, plan_url=plan_url, specialization=specialization, link=link)
        await session.commit()
        await session.refresh(plan)
        return plan




async def search_study_plans(query):
    async with async_session() as session:
        query_norm = normalize_arabic(query.lower())
        words = [w for w in query_norm.split() if len(w) > 1]

        # ponytail: basic SQL LIKE pre-filter, full normalize_arabic in Python
        like_pattern = f"%{query_norm}%"
        stmt = select(StudyPlan).where(
            StudyPlan.is_active == True,
            (StudyPlan.title.ilike(like_pattern)) |
            (StudyPlan.faculty.ilike(like_pattern)) |
            (StudyPlan.description.ilike(like_pattern))
        )
        result = await session.execute(stmt)
        candidates = result.scalars().all()

        found = []
        for plan in candidates:
            searchable = normalize_arabic(" ".join(filter(None, [
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


# ==================== Book Groups ====================
async def get_all_book_groups():
    async with async_session() as session:
        result = await session.execute(
            select(BookGroup).where(BookGroup.is_active == True)
        )
        return result.scalars().all()

async def get_book_group_by_id(group_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(BookGroup).where(BookGroup.id == group_id)
        )
        return result.scalar_one_or_none()

async def create_book_group(title: str, description: str = None, group_tag: str = None):
    async with async_session() as session:
        group = BookGroup(title=title, description=description, group_tag=group_tag)
        session.add(group)
        await session.commit()
        await session.refresh(group)
        return group

async def update_book_group(group_id: int, title: str = None, description: str = None, group_tag: str = None, channel_message_id: int = None):
    async with async_session() as session:
        group = (await session.execute(select(BookGroup).where(BookGroup.id == group_id))).scalar_one_or_none()
        if not group:
            return None
        update_fields(group, title=title, description=description, group_tag=group_tag, channel_message_id=channel_message_id)
        await session.commit()
        await session.refresh(group)
        return group

async def delete_book_group(group_id: int):
    async with async_session() as session:
        books_stmt = select(Book).where(Book.group_id == group_id)
        books_result = await session.execute(books_stmt)
        books = books_result.scalars().all()
        for book in books:
            await session.delete(book)

        stmt = select(BookGroup).where(BookGroup.id == group_id)
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()

        if group:
            await session.delete(group)
            await session.commit()
            return True
        return False


# ==================== Books ====================
async def add_book(title, description=None, author=None, file_url=None, group_id=None, link=None):
    async with async_session() as session:
        book = Book(title=title, description=description, author=author,
                    file_url=file_url, group_id=group_id, link=link)
        session.add(book)
        await session.commit()
        await session.refresh(book)
        return book

async def get_all_books():
    async with async_session() as session:
        result = await session.execute(select(Book).where(Book.is_active == True))
        return result.scalars().all()

async def get_books_by_group(group_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Book).where(Book.is_active == True, Book.group_id == group_id)
        )
        return result.scalars().all()

async def get_book_by_id(book_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Book).where(Book.id == book_id)
        )
        return result.scalar_one_or_none()

async def search_books(query):
    async with async_session() as session:
        query_norm = normalize_arabic(query.lower())
        words = [w for w in query_norm.split() if len(w) > 1]

        like_pattern = f"%{query_norm}%"
        stmt = select(Book).where(
            Book.is_active == True,
            (Book.title.ilike(like_pattern)) |
            (Book.description.ilike(like_pattern))
        )
        result = await session.execute(stmt)
        candidates = result.scalars().all()

        found = []
        for book in candidates:
            searchable = normalize_arabic(" ".join(filter(None, [
                book.title or "",
                book.description or ""
            ])).lower())

            if query_norm in searchable:
                found.append(book)
            elif words and any(w in searchable for w in words):
                found.append(book)

        return found


async def delete_book(book_id):
    async with async_session() as session:
        await session.execute(delete(Book).where(Book.id == book_id))
        await session.commit()


# ==================== Channel Groups ====================
async def get_all_channel_groups():
    async with async_session() as session:
        result = await session.execute(select(ChannelGroup).order_by(ChannelGroup.created_at.desc()))
        return result.scalars().all()

async def get_active_channel_groups():
    async with async_session() as session:
        result = await session.execute(select(ChannelGroup).where(ChannelGroup.is_active == True).order_by(ChannelGroup.created_at.desc()))
        return result.scalars().all()

async def add_channel_group(chat_id, title, type, member_count=0, invite_link=None):
    async with async_session() as session:
        existing = await session.execute(select(ChannelGroup).where(ChannelGroup.chat_id == chat_id))
        if existing.scalar_one_or_none():
            return None
        group = ChannelGroup(chat_id=chat_id, title=title, type=type, member_count=member_count, invite_link=invite_link)
        session.add(group)
        await session.commit()
        await session.refresh(group)
        return group

async def toggle_channel_group(group_id):
    async with async_session() as session:
        result = await session.execute(select(ChannelGroup).where(ChannelGroup.id == group_id))
        group = result.scalar_one_or_none()
        if group:
            group.is_active = not group.is_active
            await session.commit()
            await session.refresh(group)
        return group

async def update_channel_group(group_id, **kwargs):
    async with async_session() as session:
        result = await session.execute(select(ChannelGroup).where(ChannelGroup.id == group_id))
        group = result.scalar_one_or_none()
        if group:
            for key, value in kwargs.items():
                setattr(group, key, value)
            await session.commit()
            await session.refresh(group)
        return group

async def delete_channel_group(group_id):
    async with async_session() as session:
        result = await session.execute(select(ChannelGroup).where(ChannelGroup.id == group_id))
        group = result.scalar_one_or_none()
        if group:
            await session.delete(group)
            await session.commit()
            return True
        return False

async def get_channel_group_by_chat_id(chat_id):
    async with async_session() as session:
        result = await session.execute(select(ChannelGroup).where(ChannelGroup.chat_id == chat_id))
        return result.scalar_one_or_none()


async def get_official_channel():
    async with async_session() as session:
        result = await session.execute(
            select(ChannelGroup).where(
                ChannelGroup.type == 'channel',
                ChannelGroup.is_official == True,
                ChannelGroup.is_active == True
            )
        )
        return result.scalar_one_or_none()


async def set_official_channel(group_id: int):
    async with async_session() as session:
        result = await session.execute(select(ChannelGroup).where(ChannelGroup.id == group_id))
        group = result.scalar_one_or_none()
        if not group:
            return None
        if group.type != 'channel':
            return False
        await session.execute(
            update(ChannelGroup)
            .where(ChannelGroup.type == 'channel')
            .values(is_official=False)
        )
        await session.execute(
            update(ChannelGroup)
            .where(ChannelGroup.id == group_id)
            .values(is_official=True)
        )
        await session.commit()
        result = await session.execute(select(ChannelGroup).where(ChannelGroup.id == group_id))
        return result.scalar_one_or_none()


# ==================== Spam Patterns ====================
async def save_spam_pattern(content: str):
    async with async_session() as session:
        existing = await session.execute(
            select(SpamPattern).where(SpamPattern.content == content).limit(1)
        )
        if existing.scalar_one_or_none():
            return  # already saved
        session.add(SpamPattern(content=content))
        await session.commit()


async def get_all_spam_patterns():
    async with async_session() as session:
        result = await session.execute(
            select(SpamPattern).order_by(SpamPattern.created_at.desc())
        )
        return result.scalars().all()


async def delete_spam_pattern(pattern_id: int):
    async with async_session() as session:
        await session.execute(
            delete(SpamPattern).where(SpamPattern.id == pattern_id)
        )
        await session.commit()


async def check_spam_pattern(content: str) -> bool:
    async with async_session() as session:
        result = await session.execute(
            text("SELECT id FROM spam_patterns WHERE content = :content LIMIT 1"),
            {"content": content}
        )
        return result.first() is not None


# ==================== Query Cache ====================
async def get_cached_response(query: str) -> dict | None:
    normalized = normalize_arabic(query).strip().lower()
    logger.info(f"[CACHE DB] Searching for normalized_query: {normalized[:50]}")

    async with async_session() as session:
        result = await session.execute(
            select(QueryCache)
            .where(QueryCache.normalized_query == normalized)
            .limit(1)
        )
        cache = result.scalar_one_or_none()
        logger.info(f"[CACHE DB] Found: {cache is not None}")

        if cache:
            cache.hit_count += 1
            cache.last_used = func.now()
            await session.commit()
            return {
                "title": cache.response_title,
                "link": cache.response_link,
                "text": cache.response_text,
            }

    return None


async def cache_response(query: str, title: str, link: str = None, text: str = None):
    normalized = normalize_arabic(query).strip().lower()
    logger.info(f"[CACHE DB] Caching key: {normalized[:50]}")

    async with async_session() as session:
        result = await session.execute(
            select(QueryCache)
            .where(QueryCache.normalized_query == normalized)
            .limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.hit_count += 1
            existing.last_used = func.now()
        else:
            cache = QueryCache(
                query=query,
                normalized_query=normalized,
                response_title=title,
                response_link=link,
                response_text=text,
            )
            session.add(cache)

        await session.commit()
