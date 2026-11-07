import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from atguigu.app.models.models import Base
from atguigu.common.event_loop import run_async
from atguigu.common.settings import get_settings

# 1. sdk依赖           from  pathlib import Path
# 2. 三方依赖           from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
# 3. 自己依赖           from atguigu.common.settings import get_settings

# 1. 创建引擎
async_engine = create_async_engine(get_settings().database_url, echo=False)

# 2. 创建session工厂
session_factory = async_sessionmaker(async_engine, expire_on_commit=False)


# 3. 获取session
async def get_async_session() -> AsyncGenerator[AsyncSession]:
    async  with session_factory() as session:
        try:
            yield session  # 思考：不直接return  选择用yield.  结论：防止数据库连接出现oom情况（资源不够用）
        except Exception as exc:
            await session.rollback()
            raise exc


async def init_db():
    async  with async_engine.begin() as conn:
        logger.info("数据库表准备初始化")
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表初始化成功")


if __name__ == '__main__':
    run_async(init_db())
