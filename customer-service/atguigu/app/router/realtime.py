import asyncio
import logging

from atguigu.app.services.auth import decode_access_token
from atguigu.infrastucture.redis import redis_client

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
from typing import Any

from fastapi import APIRouter, WebSocket, status

router = APIRouter(tags=["实时事件推送的路由"])


@router.websocket("/api/v1/realtime")
async def get_realtime_endpoint(ws: WebSocket):
    """
    职责：负责将redis通道的数据 沿着ws通道推送给前端
    调用时机：页面主要加载，立刻触发该接口的调用。
    websocket/sse:
    sse:(server send event):单向负责将服务端数据推送给前端。数据格式固定要求
    websocket：双向（服务端数据推送给前端 前端也能将数据发送给服务端） 没有对数据格式有硬性要求
    :param ws:
    :return:
    """
    # 1. 建立websocket连接(将普通的http协议 升级为ws协议)
    await ws.accept()

    # 2.  获取前端发送过来的认证信息
    try:
        auth_info: dict[str, Any] = await ws.receive_json()
        access_token = auth_info['token']
    except Exception as exc:
        logger.exception("用户认证信息获取失败:%s", str(exc))
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="用户未认证")
        return

    # 3. 根据认证信息获取用户信息
    current_user = decode_access_token(access_token)

    target_channel = current_user.user_id if current_user.role == "user" else "staff"

    # 4. 注册通道到Redis
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(target_channel)

    # 5. 发送成功注册通道到Redis中
    await ws.send_json({"event_type": "connected"})  # 让前端右上角显示"在线"

    async def forward_event():
        # 6. 接收指定通道数据
        async for message in pubsub.listen():
            if message["type"] == "message":
                event_data = message["data"]
                await ws.send_text(event_data)  # 将通道的数据，给前端使用  RedisError(Exception)

    async def disconnected():
        # 7. 服务端监听ws通道有没有关闭
        while True:
            await ws.receive_text()  # WebSocketDisconnectedError.

    # 8. 并发执行两个协程任务
    tasks = [
        asyncio.create_task(forward_event()),
        asyncio.create_task(disconnected())
    ]

    # --------------------------------------优雅关闭--------------------------------------
    # 9. 对任务状态监听
    # 任务做完了。【协程任务执行期间，正常结束，协程任务执行期间，出现了异常】
    _, pending = await asyncio.wait(tasks,
                                    return_when=asyncio.FIRST_COMPLETED)  # done:监听多个协程任务执行期间，如果某一个协程任务做完了，会将这个协程任务对象返回， pending：另外没有做完的协程任务对象

    # 10. 取消另外一个未完成协程任务
    for pend in pending:
        pend.cancel()  # 真正的让事件循环线程将这个协程任务取消掉。 发送一个同步CancelError的信号。

    # 让事件循环线程获取到执行协程任务的控制权
    # gather:协程任务做聚合管理
    # wait: 协程任务监听器
    # await asyncio.sleep(10)
    await  asyncio.gather(*tasks, return_exceptions=True)  # 等没有出现异常的那个协程任务 彻底执行完
