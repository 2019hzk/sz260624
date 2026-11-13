import json
from typing import Any
from dataclasses import dataclass

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage

from atguigu.app.schemas import AgentRunRequest
from atguigu.common.settings import get_settings


@dataclass(frozen=True, slots=True)
class AgentRunContext:
    access_token: str  # 工具执行的时候要用（调用电商服务，要求提供认证信息）
    trace_id: str  # 工具执行的时候用(工具结果要保存到agent_too_call表中需要)


def build_messages(payload: AgentRunRequest) -> list[BaseMessage]:
    """
    职责： 标准化消息对象为LangChain的消息对象
    :param payload:
    :return:
    """

    # 1. 获取历史消息
    history_messages: list[dict[str, Any]] = _build_history_messages(payload.history)

    # 2. 标准化消息对象
    messages: list[BaseMessage] = [
        HumanMessage(content=_format_message(history_message))
        if history_message['role'] == "USER" else
        AIMessage(content=_format_message(history_message))
        for history_message in history_messages
    ]

    # 3. 当前轮次消息
    current_messages = _build_current_messages(payload.messages)

    messages.append(HumanMessage(content=current_messages))

    # 4. 返回(历史对话消息 当前轮次消息)
    return messages


def _build_history_messages(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    职责：构建历史消息（裁剪）
    裁剪策略：
    1。根据历史消息条数(留30条)
    2. 字符内容长度(12000)
    3. 预留历史消息列表中的第一条消息是USER角色开始留

    :param history:
    :return:
    """

    settings = get_settings()

    # 1. 最新的历史消息裁剪
    candidate_history_messages = history[-settings.history_message_limit:]

    usage_total = 0

    # 2. 控制消息的字符长度
    messages = []
    for history_messages in reversed(candidate_history_messages):
        message_content = _format_message(history_messages)

        if len(message_content) + usage_total > settings.history_character_budget:
            break
        messages.append(history_messages)
        usage_total = usage_total + len(message_content)

    # 3. 收集的历史消息反转
    messages.reverse()

    # 4. 获取用户角色的消息
    user_role_message_index = next((index for index, message in enumerate(messages) if message['role'] == "USER"), None)

    return messages[user_role_message_index:] if user_role_message_index is not None else messages


def _build_current_messages(messages: list[dict[str, Any]]) -> str:
    """
    职责：将当前轮次的消息都拼接成一个"大"字符串
    :param messages:
    :return:
    """

    # 1. 获取当前轮次消息内容列表
    message_contents = [_format_message(message) for message in messages]

    # 2. 当前轮次消息长度(单条)
    if len(message_contents) == 1:
        return message_contents[0]

    # 3. 当前轮次消息长度(多条)#
    items = "\n".join(f"{index}. {content}" for index, content in enumerate(message_contents, start=1))
    return "用户当前发送了多条消息，请您作为一个整体来理解:\n" + items


def _format_message(message: dict[str, Any]) -> str:
    """
    职责：格式化消息,返回消息内容
    :param message:
    :return:
    """

    # 1. 获取文本消息内容
    if message['type'] == "text":  # {"text":""}
        return message['content'].get('text')

    # 2. 获取对象消息内容
    message_content = message['content']

    return "消息是一个对象，结构是:\n" + json.dumps(message_content, ensure_ascii=False, indent=2)
