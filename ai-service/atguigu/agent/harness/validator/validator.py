"""

校验器

"""
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from atguigu.agent.harness.tools.catalog import TOOL_CATALOG, ToolCategory
from atguigu.agent.llm.output import AgentOutput
from atguigu.app.models.enums import ReplyType, ToolResultCode
from atguigu.app.models.models import AgentToolCall


class ValidateAgentOutError(ValueError):
    pass


from atguigu.agent.harness.validator.action import validate_page_action
from atguigu.agent.harness.validator.answer import validate_answer
from atguigu.agent.harness.validator.jev import check_output
# 降级兜底的回复内容
BUSINESS_FAILURE_MESSAGE = "暂时无法查询到可靠的订单、商品、物流或售后信息，请您稍后重试，或直接发送“转人工”由人工客服为您处理。"


class Validator:

    def __init__(self, session: AsyncSession):
        self._session = session

    async def validate_agent_output(self,
                                    agent_output: AgentOutput,
                                    trace_id: str,
                                    skill_code: str | None
                                    ) -> dict[str, Any]:
        """
        职责： 校验Agent输出的结构化对象的内容（value）
        :param agent_output:
        :param trace_id:
        :return:
        """

        # 1. 获取回复类型
        reply_type = agent_output.reply_type

        # 2. 查询工具调用记录(排除掉GUIDANCE类型工具)
        stmt = select(AgentToolCall).where(AgentToolCall.trace_id == trace_id).order_by(AgentToolCall.created_at)
        tool_calls = list((await self._session.scalars(stmt)).all())

        # 3. 根据四种回复类型分别校验
        # 3.1 校验回复类型是可信答案（ANSWER）
        if ReplyType.ANSWER == reply_type:
            """有可能是用户读【写】任务，处理后的结果"""

            # a) skill-tools闭环（带了skill码 一定要调用工具）
            if skill_code is not None and not tool_calls:
                raise ValidateAgentOutError(
                    f"加载领域技能码{skill_code}，但是没有调用工具查询获取回复结果，请调用工具查询")

            # ①：skill码没有(普通寒暄，校验  【ORDER_001 订单已经发货了。】 你好，你想咨询什么问题 )
            # ②：skill有且也调用了工具
            # b) 获取到业务类型的工具调用记录
            bs_tool_calls = [bs_tool_call for bs_tool_call in tool_calls if
                             TOOL_CATALOG.get_tool_category(bs_tool_call.tool_name) == ToolCategory.BUSINESS]

            # c) 过滤掉知识检索类型的工具，只掉用知识工具，不校验（TODO校验）
            if tool_calls and not bs_tool_calls:
                return build_result(
                    ReplyType.ANSWER,
                    agent_output.text  # LLM回复内容返回了
                )

            # d) 获取调用成功【工具记录结果result['code']!= TOOL_CALL_FAILED】的业务类型的工具
            successful_bs_tool_calls = [sbs_tool_call for sbs_tool_call in bs_tool_calls if
                                        sbs_tool_call.result['code'] != ToolResultCode.TOOL_CALL_FAILED]

            # e) 所有业务工具都调用失败，明确拒绝降级兜底回复
            if bs_tool_calls and not successful_bs_tool_calls:
                return build_result(
                    ReplyType.DECLINE,  # 自己构建明确的拒绝
                    BUSINESS_FAILURE_MESSAGE
                )

            # f) 有成功业务工具（校验ANSWER）
            validate_answer(agent_output.text, successful_bs_tool_calls)

            # g) Jev 语义护栏校验answer
            await check_output(agent_output.text, successful_bs_tool_calls)


            # h) 校验页面行动
            page_action: dict[str, Any] = validate_page_action(successful_bs_tool_calls, agent_output.page_action)

            # h) 返回
            return build_result(
                ReplyType.ANSWER,
                agent_output.text,
                page_action=page_action
            )

        # 3.2 校验回复类型是转人工请求（REQUEST_HANDOFF）
        if ReplyType.REQUEST_HANDOFF == reply_type:
            # a) 校验转人工摘要是否携带
            if agent_output.handoff_summary is None:
                raise ValidateAgentOutError(f"请求转人工必须提供 handoff_summary")

            # b) 构建转人工请求
            return build_result(
                ReplyType.REQUEST_HANDOFF,
                agent_output.text,
                request_summary=agent_output.handoff_summary
            )

        # 3.3 校验回复类型意图澄清（CLARIFY）
        if ReplyType.CLARIFY == reply_type:
            # a) 构建澄清选项卡
            choices = _build_clarify_choices(tool_calls)

            # b) 返回
            return build_result(
                ReplyType.CLARIFY,
                agent_output.text,
                choices=choices
            )

        # 3.4 校验回复类型是明确拒绝（DECLINE）
        return build_result(
            ReplyType.DECLINE,
            BUSINESS_FAILURE_MESSAGE
        )


def build_result(
        reply_type: ReplyType,
        reply_text: str,
        *,
        request_summary: str | None = None,
        page_action: dict[str, Any] | None = None,
        choices: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """
    职责：统一返回给Customer-service结构
    1. 回复类型
    2. 回复答案（可信）
    3. 转人工的摘要
    4. 页面行动需要的按钮信息
    5. 澄清选项卡（服务端自己构建的）

    :return:
    """
    return {
        "reply_type": reply_type,
        "text": reply_text,
        "summary": request_summary,
        "page_action": page_action,
        "choices": choices
    }


def _build_clarify_choices(tool_calls: list[AgentToolCall]) -> list[dict[str, Any]] | None:
    """
    只对订单做澄清：
    任务：我想取消订单------>选项卡【list_order】-----[]
    :return:
    """

    for tool_call in tool_calls:

        if tool_call.tool_name == "list_orders" and tool_call.success == True:
            return [
                {
                    "object_type": "order",
                    "object_id": order["id"],
                    "label": f"{order['id']} · {'、'.join(item['product_name'] for item in order['items'])}",
                    "description": f"¥{order['total_amount']} · {order['status_label']}",
                }
                for order in tool_call.result['data'][:5]  # 五个单
            ]

    return None
