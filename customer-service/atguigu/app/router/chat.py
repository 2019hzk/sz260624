from fastapi import APIRouter

from atguigu.app.schemas import ChatMessageRequest
from atguigu.app.dependencies import ChatServiceDep, UserRoleDep

router = APIRouter(prefix="/api/v1/chat", tags=["会话管理路由:对话、加载历史会话消息"])


@router.post("/messages")
async def chat_endpoint(payload: ChatMessageRequest,
                        service: ChatServiceDep,
                        user_role_dep: UserRoleDep):
    await service.process_chat_message(user_role_dep.user_id, payload)
