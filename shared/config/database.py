from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from ..models.base import Base
from .settings import settings

engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)