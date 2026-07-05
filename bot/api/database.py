from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.config import DATABASE_URL

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


async def get_db():
    async with async_session() as session:
        yield session
