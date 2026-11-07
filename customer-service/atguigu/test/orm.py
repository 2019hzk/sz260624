import asyncio
import selectors

from sqlalchemy import String, select
from sqlalchemy.exc import MissingGreenlet
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from atguigu.common.settings import get_settings

engine = create_async_engine(url=get_settings().database_url, echo=False)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    # 自增主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    age: Mapped[int] = mapped_column(default=18)

    def __repr__(self):
        return f"id:{self.id},name:{self.name},age:{self.age}"


async def crud_demo():
    async with AsyncSessionFactory() as session:
        # print("\n1. 新增")
        # user = User(name="张三", age=20)
        # session.add(user)
        # await session.commit()  # 直接 commit
        # print(f"创建成功: {user}")

        print("\n2. 查询")
        stmt = select(User)
        db_user = (await session.scalars(stmt)).all()
        print(f"查询结果: {db_user}")

        # print("\n3. 修改")
        # if db_user:
        #     db_user.age = 25
        #     await session.commit()
        # print(f"修改后: {db_user}")

        # print("\n4. 删除")
        # if db_user:
        #     await session.delete(db_user)
        #     await session.commit()


async def compare_expire_on_commit():
    async with AsyncSessionFactory() as session:
        user_tom = User(name="Tom", age=18)
        session.add(user_tom)

        # commit 成功后，若 expire_on_commit=True，SQLAlchemy 会把 user_tom 内存里的属性全部清空（标记为过期）
        await session.commit()
        try:
            print(f"尝试在 commit 后直接读取属性: user_tom.id = {user_tom.name}")
        except MissingGreenlet as e:
            print(f"原因：commit 后属性已过期，异步环境禁止隐式发起同步查询！\n   报错详情: {e}")


async def main():
    # 1. 初始化建表
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)
    #     await conn.run_sync(Base.metadata.create_all)

    # Base.metadata.create_all(conn)

    # 2. 运行CRUD
    await crud_demo()

    # 3. 运行 expire_on_commit 对比
    # await compare_expire_on_commit()

    # 4. 关闭引擎
    await engine.dispose()


if __name__ == '__main__':
    pass
    # windows自带的的事件经常和三方的依赖出现不兼容的情况。
    # 解决方案：换最底层能够兼容三方依赖的事件循环(select对应的多路复用机制的事件循环即可)
    # asyncio.run(main())
    # 解决方案一
    asyncio.run(main(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
    # # 解决方案二
    # asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    # asyncio.run(main())
