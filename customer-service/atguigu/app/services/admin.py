from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException

from atguigu.app.models.enums import HandoffStatus, ConversationMode, MessageRole
from atguigu.app.models.models import Handoff, Message, Conversation
from atguigu.app.schemas import ReplyRequest
from atguigu.app.services.realtime import RealtimeService
from atguigu.common.settings import get_settings
from atguigu.common.utils import get_uid, get_utcnow


class AdminService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._settings = get_settings()
        self._realtime_service = RealtimeService(session)
    #----------------------------------工单相关-------------------------------------
    def create_handoff(self,
                       conversation: Conversation,
                       *,
                       summary: str
                       ):
        handoff = Handoff(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            summary=summary,
            status=HandoffStatus.WAITING
        )

        self._session.add(handoff)

    async def get_handoffs(self) -> list[Handoff]:
        """
        职责：获取所有用户的工单[有效转态]列表信息
        :return:
        """
        stmt = select(Handoff).where(Handoff.status.in_([HandoffStatus.WAITING, HandoffStatus.ACTIVE])).order_by(
            Handoff.created_at
        )
        return list((await  self._session.scalars(stmt)).all())

    async def accept_handoff(self, handoff_id: str, staff_id: str):
        """
        职责：接收工单（1.接收的工单是哪个 2. 哪个客服接收）
        1.并发抢单
        场景：张三客服抢到该用户的单，另外一个客服在来点击抢到，拒绝掉。
        :param handoff_id:
        :param staff_id:
        :return:
        """
        # 1. 获取工单以及工单对应的会话信息
        handoff, conversation = await self._get_handoff_conversation(handoff_id)

        # 2. 获取工单状态
        if handoff.status == HandoffStatus.ACTIVE:
            raise HTTPException(status_code=409, detail="该工单已经被接入，请勿重试抢单")

        # 3. 修改工单的状态以及会话的模式
        # 3.1 修改工单的信息
        handoff.status = HandoffStatus.ACTIVE  # 并发写（没有问题，覆盖写。不是追加写）
        handoff.staff_id = staff_id

        # 3.2 修改会话的模式
        conversation.mode = ConversationMode.HUMAN

        # 4. 保存人工客服的回复(引导语:开场白)
        self._save_human_reply(conversation, reply_text=f"客服 {staff_id} 已经接入工单，请问您有什么需要帮助的?")

        # 5. 提交
        await self._session.commit()

    async def reply_messages(self, handoff_id: str, payload: ReplyRequest):
        """
        职责： 人工回复
        :param handoff_id:
        :param payload
        :return:
        """
        # 1. 获取工单以及工单对应的会话信息
        _, conversation = await self._get_handoff_conversation(handoff_id)

        # 2. 保存人工客服的回复内容
        self._save_human_reply(conversation, reply_text=payload.text)

        # 3. 统一提交
        await  self._session.commit()

    async def resolve_handoff(self, handoff_id: str):
        """
        职责：结束工单
        :param handoff_id:
        :return:
        """

        # 1. 获取工单以及工单对应的会话信息
        handoff, conversation = await self._get_handoff_conversation(handoff_id)

        # 2. 修改工单的状态以及会话的模式
        # 2.1 修改工单状态为结束
        handoff.status = HandoffStatus.RESOLVED
        # 2.2 修改会话模式为AI
        conversation.mode = ConversationMode.AI

        # 3. 保存人工客服的回复内容(引导语:结束语)
        self._save_human_reply(conversation, reply_text="人工客服已经结束，稍后由AI 继续为你服务。")

        # 4. 统一提交
        await  self._session.commit()

    async def get_handoff_messages(self, handoff_id: str) -> dict[str, Any]:
        """
        职责：管理工单对应会话的消息

        :param handoff_id:
        :return:
        """
        stmt = select(Message).join(Handoff, Message.conversation_id == Handoff.conversation_id).where(
            Handoff.id == handoff_id
        ).order_by(Message.id)

        conversation_messages = (await self._session.scalars(stmt)).all()
        return {"messages": conversation_messages}

    # ----------------------------------指标相关-------------------------------------
    async def get_metrics(self) -> dict[str, Any]:
        """
        职责：获取指标信息(数量)
        :return:
        """
        return {
            "conversations": await self._get_count(Conversation.id),
            "handoffs": await self._get_count(Handoff.id),
            "queued": await self._get_count(Conversation.id, Conversation.mode == ConversationMode.QUEUED),
            "human": await self._get_count(Conversation.id, Conversation.mode == ConversationMode.HUMAN)
        }

    async def _get_handoff_conversation(self, handoff_id: str) -> tuple[Handoff, Conversation]:
        handoff = await self._session.scalar(select(Handoff).where(Handoff.id == handoff_id).with_for_update())

        conversation = await self._session.scalar(
            select(Conversation).where(Conversation.id == handoff.conversation_id).with_for_update())

        return handoff, conversation

    async def _get_count(self, col, *condition_expr) -> int:
        return await  self._session.scalar(select(func.count(col)).where(*condition_expr))

    def _save_human_reply(self,
                          conversation: Conversation,
                          reply_text: str):
        """
        职责： 保存人工客服的回复
        1. 对内将客服接收到工单信息保存到messages表
        2. 对外将客服接收到工单通知给用户
        :param conversation:
        :param reply_text:
        :return:
        """
        # 1. 构建消息
        message = Message(
            message_id=get_uid("msg"),
            conversation_id=conversation.id,
            role=MessageRole.HUMAN,
            message_type="text",
            content={"text": reply_text}
        )

        self._session.add(message)

        # 2. 更新会话的激活时间
        conversation.last_active_at = get_utcnow()

        # 3. 保存事件
        self._realtime_service.add_event(message, conversation, notify_user=True, notify_staff=False)
