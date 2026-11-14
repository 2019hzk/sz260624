from enum import StrEnum


class AgentTraceStatus(StrEnum):
    """AgentTrace 执行轨迹状态"""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"



class ToolResultCode(StrEnum):
    TOOL_CALL_FAILED="TOOL_CALL_FAILED"

