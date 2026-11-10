from typing_extensions import Annotated
from fastapi import Depends, Header

from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.schemas import CurrentUser
from atguigu.app.services.admin import AdminService
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


def get_admin_service(session: SessionDep) -> AdminService:
    return AdminService(session)


AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]


def require_staff_role_auth(authorization: Annotated[str | None, Header()]) -> CurrentUser:
    return authorized_user(authorization, "staff")


StaffRoleDep = Annotated[CurrentUser, Depends(require_staff_role_auth)]


def require_admin_role_auth(authorization: Annotated[str | None, Header()]) -> CurrentUser:
    return authorized_user(authorization, "admin")


AdminRoleDep = Annotated[CurrentUser, Depends(require_admin_role_auth)]
