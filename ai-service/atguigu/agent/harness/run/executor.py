import logging
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from langchain_core.callbacks import UsageMetadataCallbackHandler

from atguigu.agent.harness.run.context import build_messages, AgentRunContext
from atguigu.app.models.enums import AgentTraceStatus
from atguigu.app.models.models import AgentTrace
from atguigu.app.schemas import AgentRunRequest, CurrentUser
from atguigu.common.settings import get_settings
from atguigu.agent.harness.validator.validator import Validator, ValidateAgentOutError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentExecutor:

    def __init__(self, session: AsyncSession, *, agent: Any):
        self._settings = get_settings()
        self._session = session
        self._agent = agent
        self._validator = Validator()

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
            run_result = await self._invoke_agent(payload, current_user, agent_traces)
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

    async def _invoke_agent(self,
                            payload: AgentRunRequest,
                            current_user: CurrentUser,
                            agent_traces: AgentTrace) -> dict[str, Any] | None:
        """
        职责：调用Agent对象真正完成推理
        :param payload:
        :param current_user:
        :param agent_traces:
        :return:
        """
        # 1. 构建LangChain标准的消息对象
        messages = build_messages(payload)

        call_back = UsageMetadataCallbackHandler()

        # 2. 构建上下文
        context = AgentRunContext(
            access_token=current_user.access_token,
            trace_id=agent_traces.id
        )

        # 3. Agent运行
        try:
            # 3.1 调用Agent
            agent_output = await self._agent.ainvoke({"messages": messages},
                                                     context=context,
                                                     config={
                                                         "callbacks": [call_back]
                                                     })

            # run_result = self._validator.validate_agent_output(agent_output)
            return agent_output
            # 3.2 调用Agent期间出错
        except ValidateAgentOutError as exc:
            # 3.3 重试纠错（把执行完的结果以及【我要求你根据上一次结果的信息，给我重试】指令）
            pass
        finally:
            # 3.4 统计token用量
            input_tokens, output_tokens = self._summary_tokens(call_back)
            agent_traces.input_tokens = input_tokens
            agent_traces.output_tokens = output_tokens

    def _summary_tokens(self, call_back: UsageMetadataCallbackHandler) -> tuple[int, int]:
        """
        职责：统计调用Agent期间Token用量
        :return:
        """
        all_model_usage: list[dict[str, Any]] = list(call_back.usage_metadata.values())

        input_tokens = sum(model_usage.get('input_tokens', 0) for model_usage in all_model_usage)
        output_tokens = sum(model_usage.get('output_tokens', 0) for model_usage in all_model_usage)

        return input_tokens, output_tokens
