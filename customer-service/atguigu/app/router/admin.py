from fastapi import APIRouter

from atguigu.app.dependencies import AdminServiceDep, StaffRoleDep, AdminRoleDep
from atguigu.app.schemas import ReplyRequest

router = APIRouter(prefix="/api/v1", tags=["管理端路由接口"])


@router.get("/handoffs")
async def get_handoffs_endpoint(
        service: AdminServiceDep,
        _: StaffRoleDep
):
    return await    service.get_handoffs()


@router.get("/handoffs/{handoff_id}/messages")
async def get_handoff_messages_endpoint(
        service: AdminServiceDep,
        handoff_id: str,
        _: StaffRoleDep
):
    return await    service.get_handoff_messages(handoff_id)


@router.post("/handoffs/{handoff_id}/accept")
async def accept_handoff_endpoint(
        service: AdminServiceDep,
        handoff_id: str,
        staff_role: StaffRoleDep
):
    await    service.accept_handoff(handoff_id, staff_role.user_id)


@router.post("/handoffs/{handoff_id}/messages")
async def reply_messages_endpoint(
        service: AdminServiceDep,
        handoff_id: str,
        payload: ReplyRequest,
        _: StaffRoleDep
):
    await    service.reply_messages(handoff_id, payload)


@router.post("/handoffs/{handoff_id}/resolve")
async def resolve_handoff_endpoint(
        service: AdminServiceDep,
        handoff_id: str,
        _: StaffRoleDep
):
    await    service.resolve_handoff(handoff_id)




@router.get("/admin/metrics")
async def get_metrics_endpoint(
        service: AdminServiceDep,
        _: AdminRoleDep
):
    return await    service.get_metrics()
