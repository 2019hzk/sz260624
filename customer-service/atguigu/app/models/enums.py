from enum import StrEnum


class ConversationMode(StrEnum):
    """
    会话模式
    """
    AI = "AI"
    QUEUED = "QUEUED"
    HUMAN = "HUMAN"
    CLOSED = "CLOSED"


class MessageRole(StrEnum):
    """
     消息角色
    """
    USER = "USER"
    AI = "AI"
    HUMAN = "HUMAN"


class TurnStatus(StrEnum):
    """
    轮次状态
    """
    COLLECTING = "COLLECTING"  # 起始态
    RUNNING = "RUNNING"  # 中间态
    COMPLETED = "COMPLETED"  # 最终态
    FAILED = "FAILED"  # 最终态
    SUPERSED = "SUPERSED"  # 最终态


class HandoffStatus(StrEnum):
    """
    工单状态
    """

    WAITING = "WAITING"  # 有效(客服暂未接入)
    ACTIVE = "ACTIVE"  # 有效(客服已经接入)
    RESOLVED = "RESOLVED"  # 无效(客服关闭工单)
