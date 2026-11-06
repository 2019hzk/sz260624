from typing_extensions import Annotated
from fastapi import Depends, Header

from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.schemas import CurrentUser
from atguigu.app.services.auth import authorized_user
from atguigu.app.services.chat import ChatService
from atguigu.infrastucture.db import get_async_session

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


def get_chat_service(session: SessionDep) -> ChatService:
    return ChatService(session)


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


def require_user_role_auth(authorization: Annotated[str | None, Header()]) -> CurrentUser:
    return authorized_user(authorization, "user")


UserRoleDep = Annotated[CurrentUser, Depends(require_user_role_auth)]
