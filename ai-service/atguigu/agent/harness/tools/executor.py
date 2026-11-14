import json
import time
from typing import Any

from pydantic import BaseModel
from langchain.tools import ToolRuntime

from atguigu.agent.harness.run.context import AgentRunContext
from atguigu.app.models.enums import ToolResultCode
from atguigu.app.models.models import AgentToolCall
from atguigu.infrastructure.db import async_session_factory


class ToolResult(BaseModel):
    """
    业务侧用的
    """
    success: bool
    code: str
    message: str
    data: Any | None = None   # dict[str,Any]  list[dict[str,Any]]


class ToolExecutor:

    async def execute_tool(self,
                           runtime: ToolRuntime[AgentRunContext],
                           tool_name: str,
                           arguments: dict[str, Any],
                           *,
                           operator: Any):
        """

        :return:
        """
        # 1. 发送请求获取接口数据
        start_time = time.perf_counter()
        try:
            response: dict[str, Any] = await  operator()        # 执行失败(调用电商服务，发送请求，走网络【网络抖动、超时、电商服务宕机】)
            tool_result = ToolResult.model_validate(response)   # 基本不会失败
        except Exception as exc:
            # 不抛出异常（对异常做转译）---->入库(程序看)、给LLM(大模型看)，有好的明确说明，暂无获取到业务数据 大概率不会在调用失败的工具【继续调】
            tool_result = ToolResult(
                success=False,
                code=ToolResultCode.TOOL_CALL_FAILED,             # 业务工具全部调用失败了【TOOL_CALL_FAILED】===直接降级
                message=f"业务工具调用失败，无法获取可靠依据，异常原因:{exc}"
            )

        # 2. 入库
        await self._sava_tool_result(
            trace_id=runtime.context.trace_id,
            tool_call_id=runtime.tool_call_id,
            tool_name=tool_name,
            arguments=arguments,
            result=tool_result.model_dump(),
            success=tool_result.success,
            latency_ms=int((time.perf_counter() - start_time) * 1000)
        )

        # 3. 直接返回工具结果给Agent---->LLM
        return json.dumps(tool_result.model_dump(), ensure_ascii=False)

    async def _sava_tool_result(self,
                                trace_id: str,
                                tool_call_id: str,
                                tool_name: str,
                                arguments: dict[str, Any],
                                result: dict[str, Any],
                                success: bool,
                                latency_ms: int
                                ):
        async  with  async_session_factory() as session:
            # 1. 构建AgentToolCall对象
            agent_tool_call = AgentToolCall(trace_id=trace_id,
                                            tool_call_id=tool_call_id,
                                            tool_name=tool_name,
                                            arguments=arguments,
                                            result=result,
                                            success=success,
                                            latency_ms=latency_ms
                                            )

            # 2. 入库
            session.add(agent_tool_call)

            # 3. 提交
            await  session.commit()


tool_executor = ToolExecutor()
