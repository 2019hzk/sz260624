from enum import StrEnum

class ReplyType(StrEnum):
    """
    回复类型
    """

    ANSWER= "ANSWER"                        # 正常回复【任务：，我想查询订单信息】
    REQUEST_HANDOFF="REQUEST_HANDOFF"       # 转人工请求【我想转接人工客服】
    CLARIFY="CLARIFY"                       # 澄清【任务：我想取消订单，没有明确目标，构建澄清选项卡】
    DECLINE="DECLINE"                       # 拒绝【任务：我想上天。业务无关、不是普通寒暄，执行任务，调用工具都失败了。】



class AgentTraceStatus(StrEnum):
    """AgentTrace 执行轨迹状态"""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"



class ToolResultCode(StrEnum):
    TOOL_CALL_FAILED="TOOL_CALL_FAILED"

