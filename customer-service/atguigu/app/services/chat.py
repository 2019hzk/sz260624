from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from atguigu.app.models.enums import MessageRole, ConversationMode, TurnStatus
from atguigu.app.models.models import Message, Conversation, ConversationTurn
from atguigu.app.schemas import ChatMessageRequest
from atguigu.common.settings import get_settings
from atguigu.common.utils import get_utcnow, get_uid


class ChatService:

    def __init__(self, session: AsyncSession):
        self._session = session
        self._settings = get_settings()

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
            # 创建轮次
            await  self._create_or_get_turn(conversation.id)  # 创建逻辑对象---AI Woker扫描turns表
        else:
            # QUEUED  HUMAN  ---->发送实时事件通知客服端  要让客服端能够收到用户的最新消息
            # 1. 创建实时事件表
            # 2. 保存(保存到哪个目标通道，以及该目标通道对应的数据是什么)   # Realtime Woker扫描realtime_events表
            pass

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
