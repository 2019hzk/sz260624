from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, select

from atguigu.common.event_loop import run_async
from atguigu.common.settings import get_settings
from atguigu.test.orm import User

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


async def main():
    async  for session in get_async_session():
        result = await session.execute(text('select 1'))
        print(result.scalar())  # 一行一列的数据


if __name__ == '__main__':
    run_async(main())
