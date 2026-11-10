import asyncio
import json
import logging

from redis import RedisError

from atguigu.app.models.models import RealtimeEvent
from atguigu.app.services.realtime import RealtimeService
from atguigu.common.event_loop import run_async
from atguigu.common.settings import get_settings
from atguigu.infrastucture.db import session_factory
from atguigu.infrastucture.redis import redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealtimeWorker:

    def __init__(self):
        self._settings = get_settings()
        self._session_factory = session_factory
        self._redis_client = redis_client

    async def start(self):
        logger.info("Realtime Worker 启动...")

        while True:
            claimed_event = await self._process_claim_event()
            if not claimed_event:
                await  asyncio.sleep(1)  # 睡眠一会 再次领取事件

    async def _process_claim_event(self) -> bool:
        """
        职责：处理领取到的事件
        :return:
        """

        async  with self._session_factory() as session:
            # 1. 实例化RealtimeService对象
            realtime_service = RealtimeService(session)

            # 2. 获取未发布的事件
            event = await realtime_service.get_unpublish_event()

            # 3. 未找到要发布的事件
            if event is None:
                return False

            # 4. 发布给Redis通道( 发送给哪个通道 给通道发送什么数据)
            try:
                await self._redis_client.publish(event.target, json.dumps(event.data, ensure_ascii=False))
            except  RedisError as exc:
                logger.exception("发送给Redis服务的%s失败,原因:%s", event.target, str(exc))
                return False

            # 5. 将该事件修改为已经发布
            await realtime_service.mark_published_event(event)

            # 6. 返回
            return True
