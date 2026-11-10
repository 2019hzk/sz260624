from typing import Literal, Any

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """
    BaseModel:核心能力，负责运行的时候做各种校验以及丰富的对象操作的api.
    """
    message_id: str = Field(description="消息唯一ID")
    type: Literal["text", "object"] = Field(description="消息内容的类型")
    content: dict[str, Any] = Field(description="消息的内容、普通文本内容、对象内容")


class CurrentUser(BaseModel):
    user_id: str
    role: Literal["user", "staff", "admin"] = "user"


class ReplyRequest(BaseModel):
    text: str
