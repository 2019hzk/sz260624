import uvicorn

from atguigu.common.event_loop import run_async
from atguigu.common.settings import get_settings


async def start_uvicorn():
    settings = get_settings()

    # 更换uvicorn启动方式为异步方式
    server = uvicorn.Server(
        config=uvicorn.Config(
            app="app.app:app",
            host=settings.app_host,
            port=settings.api_port,
            loop="none"  # 显示指定一定使用到我们自定义的事件循环
        )
    )

    await server.serve()


if __name__ == '__main__':
    run_async(start_uvicorn())
