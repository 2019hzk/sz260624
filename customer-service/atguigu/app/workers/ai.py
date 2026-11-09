import httpx
import logging
from typing import Any

from atguigu.app.services.auth import encode_access_token
from atguigu.app.services.chat import ChatService
from atguigu.infrastucture.db import session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import asyncio
from atguigu.common.settings import get_settings


class AIWorker:

    def __init__(self):

        self._settings = get_settings()

    async def start(self):
        """
        启动ai-worker
        1. 领取turn
        2. 构建ai-service的载荷
        3. 结算轮次(1.校验快照 2.保存ai-service结果)
        :return:
        """
        logger.info("AI Worker 启动...")
        # 轮询领取Turn， 并且处理
        while True:
            claimed_turn = await self._process_claim_turn()
            if not claimed_turn:
                await  asyncio.sleep(self._settings.ai_worker_poll_interval_ms / 1000)  # 睡眠一会 再次领取

    async def _process_claim_turn(self) -> bool:
        """
        职责：处理领取到的轮次Turn
        :return:
        """

        async  with  session_factory() as session:
            chat_service = ChatService(session)

            # 1. 领取turn 且构建调用ai-service需要的载荷数据
            claimed_turn_and_payload = await chat_service.claim_turn_and_build_payload()

            # 2. 判断是否领取到
            if claimed_turn_and_payload is None:
                return False

            claimed_turn, payload, user_id = claimed_turn_and_payload

            # 3. 调用ai-service
            ai_result, error = await self._call_ai_service(payload, user_id)

            # 4. 结算轮次相关信息
            await chat_service.finish_turn(claimed_turn, ai_result, error)

            return True

    async def _call_ai_service(self,
                               payload: dict[str, Any],
                               user_id: str) -> tuple[dict[str, Any] | None, Exception | None]:
        """
        职责：调用ai-service
        1. 构建ai-service请求url
        2. 携带参数[1. url  2. 头、cookies 3. 请求体]
        3. 发送请求：httpx :client
        4. 响应数据
        :param payload:
        :param user_id:
        :return:
        """

        access_token = encode_access_token(user_id)

        # a) 构建请求头
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Internal-Service-Token": self._settings.internal_service_token,
        }
        # b) 构建超时
        timeout = httpx.Timeout(self._settings.ai_timeout_seconds, connect=5)

        # c) 发送请求
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                response = await client.post(
                    f"{self._settings.ai_service_url}/internal/v1/agent/runs",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                return response.json(), None
        except Exception as exc:
            logger.exception("会话 %s 调用 AI Service 失败: %s", payload["conversation_id"], exc)
            return None, exc
