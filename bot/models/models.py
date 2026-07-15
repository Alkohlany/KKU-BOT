from sqlalchemy import Column, Integer, BigInteger, String, Boolean, Text, DateTime, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    is_subscribed = Column(Boolean, default=False)
    last_check = Column(TIMESTAMP, server_default=func.now())
    created_at = Column(TIMESTAMP, server_default=func.now())


class ChannelGroup(Base):
    __tablename__ = 'channel_groups'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False, default='group')
    member_count = Column(Integer, default=0)
    invite_link = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_official = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class AutoResponse(Base):
    __tablename__ = "auto_responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(255), nullable=False)
    response = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(BigInteger)
    file_url = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=True)
    as_document = Column(Boolean, default=False)
    file_tg_id = Column(String(200), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    source_chat_id = Column(BigInteger, nullable=True)
    source_message_id = Column(Integer, nullable=True)
    news_id = Column(Integer, ForeignKey("news.id"), nullable=True)


class BannedUser(Base):
    __tablename__ = "banned_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, nullable=False)
    reason = Column(Text)
    banned_by = Column(BigInteger)
    banned_at = Column(TIMESTAMP, server_default=func.now())


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(100))
    details = Column(Text)
    performed_by = Column(BigInteger)
    created_at = Column(TIMESTAMP, server_default=func.now())


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    image_url = Column(String(500))
    file_url = Column(String(500))
    thumbnail_url = Column(String(500))
    file_name = Column(String(255), nullable=True)
    file_type = Column(String(50), nullable=True)
    file_id = Column(String(200), nullable=True)
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime)
    created_by = Column(BigInteger)
    channel_message_id = Column(Integer, nullable=True)
    as_document = Column(Boolean, default=False)
    group_message_ids = Column(Text, nullable=True)  # JSON string: {"chat_id": message_id, ...}
    files_json = Column(Text, nullable=True)
    target_channels = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100))
    keywords = Column(String(500))
    file_url = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=True)
    as_document = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    news_id = Column(Integer, ForeignKey("news.id"), nullable=True)


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    image_url = Column(String(500))
    file_url = Column(String(500))
    file_name = Column(String(255), nullable=True)
    file_type = Column(String(50), nullable=True)
    file_id = Column(String(200), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    schedule_time = Column(DateTime, nullable=False)
    is_recurring = Column(Boolean, default=False)
    recurring_interval = Column(String(50))
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime)
    created_by = Column(BigInteger)
    as_document = Column(Boolean, default=False)
    files_json = Column(Text, nullable=True)
    target_channels = Column(Text, nullable=True)
    group_message_ids = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class StudyPlanGroup(Base):
    __tablename__ = "study_plan_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    group_tag = Column(String(100), nullable=True)
    specialization = Column(String(200), nullable=True)
    link = Column(String(500), nullable=True)
    channel_message_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    plans = relationship("StudyPlan", back_populates="group", cascade="all, delete-orphan")


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey("study_plan_groups.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    faculty = Column(String(100))
    level = Column(String(50))
    plan_url = Column(String(500))
    file_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    channel_message_id = Column(Integer, nullable=True)
    target_channels = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    group = relationship("StudyPlanGroup", back_populates="plans")


class ResponseCategory(Base):
    __tablename__ = "response_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Settings(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now())


class SpamPattern(Base):
    __tablename__ = 'spam_patterns'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
