import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from atguigu.app.models.enums import AgentTraceStatus
from atguigu.app.models.models import AgentTrace
from atguigu.app.schemas import AgentRunRequest, CurrentUser
from atguigu.common.settings import get_settings


class AgentExecutor:

    def __init__(self, session: AsyncSession, *, agent: Any):
        self._settings = get_settings()
        self._session = session
        self._agent = agent

    async def start_run(self,
                        payload: AgentRunRequest,
                        current_user: CurrentUser
                        ) -> dict[str, Any]:
        """
        运行Agent逻辑主入口

        职责：
        1. 创建Agent一次运行的轨迹【1.1 一次Agent运行不等于只调用一次LLM  1.2 用一张表存储Agent运行过程】
        2. 调用Agent执行（进行推理）
        3. 根据Agent执行的情况(正常执行完 or 出错) 记录状态
        4. 提交
        5. 返回结果
        :return:
        """

        # 1. 创建AgentTrace
        agent_traces = AgentTrace(
            conversation_id=payload.conversation_id,
            status=AgentTraceStatus.RUNNING,
            model_name=self._settings.llm_model,
            prompt_version=self._settings.prompt_version,
        )

        self._session.add(agent_traces)
        await  self._session.commit()

        # 2. 调用Agent
        start_time = time.perf_counter()
        try:
            run_result = self._invoke_agent()
        except Exception as exc:
            logger.exception("Agent推理会话 %s 任务期间出错", payload.conversation_id)
            agent_traces.status = AgentTraceStatus.FAILED
            agent_traces.result = {"text": f"AI 执行出错，原因:{exc}"}
            agent_traces.latency_ms = int((time.perf_counter() - start_time) * 1000)
            await  self._session.commit()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="AI智能体执行出错")  # customer-service调用方可以进行两次重试

        # 3. 修改Agent轨迹的状态
        agent_traces.status = AgentTraceStatus.COMPLETED
        agent_traces.result = run_result
        agent_traces.latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 4. 提交
        await  self._session.commit()

        # 5. 返回
        return run_result

if __name__ == '__main__':
    start_time = time.perf_counter()

    time.sleep(2)

    print(time.perf_counter() - start_time)
