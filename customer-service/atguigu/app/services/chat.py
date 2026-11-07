from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from atguigu.app.models.enums import MessageRole, ConversationMode
from atguigu.app.models.models import Message, Conversation
from atguigu.app.schemas import ChatMessageRequest
from atguigu.common.utils import get_utcnow


class ChatService:

    def __init__(self, session: AsyncSession):
        self._session = session

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
        conversation = self._create_or_get_conversation(user_id)

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
            pass
        else:
            # QUEUED  HUMAN  ---->发送实时事件
            pass

        # 7. 统一提交
        await self._session.commit()

    def _create_or_get_conversation(self, user_id: str) -> Conversation:
        """
        职责：返回一个有效的会话
        :param user_id:
        :return:
        """
