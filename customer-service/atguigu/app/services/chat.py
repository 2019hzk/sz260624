from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from atguigu.app.models.enums import MessageRole, ConversationMode, TurnStatus
from atguigu.app.models.models import Message, Conversation, ConversationTurn
from atguigu.app.schemas import ChatMessageRequest
from atguigu.app.services.realtime import RealtimeService
from atguigu.common.settings import get_settings
from atguigu.common.utils import get_utcnow, get_uid


class ChatService:

    def __init__(self, session: AsyncSession):
        self._session = session
        self._settings = get_settings()
        self._realtime_service = RealtimeService(session)

    async def get_chat_history(self, user_id: str) -> dict[str, Any]:
        """
        职责：获取当前用户下所有会话【活跃会话、关闭会话】的消息

        :param user_id: 用户ID
        :return:
        """

        # 1. 定义查询当前用户下所有会话的SQL
        stmt = select(Message).join(Conversation, Message.conversation_id == Conversation.id).where(
            Conversation.user_id == user_id)

        # 2. 查询SQL语句
        records = (await self._session.scalars(stmt)).all()

        # 3. 过滤消息内容
        conversation_messages = [
            {
                "conversation_id": record.conversation_id,
                "role": record.role,  # 前端展示历史对话的时候渲染图标角色
                "content": record.content  # 前端展示历史对话的消息内容
            }
            for record in records
        ]

        # 4. 获取当前用户的会话
        conversation = await self._create_or_get_conversation(user_id)
        await self._session.commit()
        # 5. 返回给前端使用
        return {
            "conversation_id": conversation.id,
            # 当前活跃会话的会话ID-----1) 供历史消息区域在展示历史消息的时候，能对当前会话的消息，做一个特殊标记【聚合：区分当前会话的消息、以及非当前会话的消息】 2）让客户区域获取到当前会话下的消息
            "conversation_mode": conversation.mode,  # 当前活跃会话的会话模式---前端右上角徽章区域展示用，刷新页面的时候，徽章变化
            "messages": conversation_messages  # 有可能是关闭会话的消息，当前活跃会话的消息

        }

    async def process_chat_message(self,
                                   user_id: str,
                                   payload: ChatMessageRequest
                                   ):
        """
        职责：处理对话逻辑
        1. 获取会话
        2. 创建消息
        3. 消息根据会话模式做分流
        3.1 AI模式，创建轮次
        3.2 人工客服模式，发送实时事件
        4. 统一提交()

        :param user_id:
        :param payload:
        :return:
        """

        # 1. 消息去重
        stmt = select(Message).where(Message.message_id == payload.message_id)
        message = await  self._session.scalar(stmt)
        if message:
            return

        # 2. 获取会话
        conversation = await self._create_or_get_conversation(user_id)

        # 3. 构建消息对象
        message = Message(message_id=payload.message_id,
                          conversation_id=conversation.id,
                          role=MessageRole.USER,
                          message_type=payload.type,
                          content=payload.content
                          )

        # 4. 保存消息到数据库
        self._session.add(message)

        # 5. 更新会话的激活时间
        conversation.last_active_at = get_utcnow()

        # 6. 消息根据会话模式分流
        if conversation.mode == ConversationMode.AI:
            # 6.1 创建轮次
            await  self._create_or_get_turn(conversation.id)  # 创建逻辑对象---AI Woker扫描turns表
        else:
            # 6.2 发送实时事件通知客服端【只是发送给客服通道一个刷新工单的信号而已。】
            self._realtime_service.add_event(message, conversation, notify_staff=True)

        # 7. 统一提交
        await self._session.commit()

    async def _create_or_get_conversation(self, user_id: str) -> Conversation:
        """
        职责：返回一个有效的（AI/QUEUED/HUMAN）【排除掉CLOSED模式】会话
        如果回话模式有效，有没有到期，如果到期了，需要关闭之前这个有效的会话，在重新创建一个新的会话。如果没有到期，直接使用该会话，无需重新创建新的
        :param user_id:
        :return:
        """

        # 1. 查询之前有效的会话
        # 1.1 定义SQL语句
        stmt = select(Conversation).where(Conversation.user_id == user_id, Conversation.mode != ConversationMode.CLOSED)

        # 1.2 执行SQL语句
        conversation = await self._session.scalar(stmt)

        # 2. 判断已有的有效会话是否过期
        if conversation:
            # 会话模式是AI && 比较时间
            timeout = timedelta(minutes=self._settings.conversation_idle_timeout_minutes)
            if conversation.mode == ConversationMode.AI and get_utcnow() - conversation.last_active_at >= timeout:
                conversation.mode = ConversationMode.CLOSED
            else:
                return conversation

        # 3. 创建新的会话
        conversation = Conversation(
            id=get_uid("conv"),
            user_id=user_id,
            mode=ConversationMode.AI
        )

        # 4. 保存
        self._session.add(conversation)

        # 5. 返回
        return conversation

    async def _create_or_get_turn(self, conversation_id: str) -> ConversationTurn:
        """
        职责：创建处于COLLECTING状态轮次（如果轮次要有，无需创建，没有，才创建）
        :param conversation_id:
        :return:
        """

        # 1. 定义查询轮次的SQL语句
        stmt = select(ConversationTurn).where(ConversationTurn.conversation_id == conversation_id,
                                              ConversationTurn.status == TurnStatus.COLLECTING
                                              )

        # 2. 查询SQL
        turn = await self._session.scalar(stmt)

        if turn is None:
            turn = ConversationTurn(
                conversation_id=conversation_id,
                status=TurnStatus.COLLECTING,
                collect_until=get_utcnow() + timedelta(milliseconds=self._settings.message_merge_delay_ms)
            )
            self._session.add(turn)

        # 3. 返回轮次
        return turn
