from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from atguigu.app.schemas import ChatMessageRequest


class ChatService:

    def __init__(self, session: AsyncSession):
        self._session = session

    async def process_chat_message(self,
                                   user_id: str,
                                   payload: ChatMessageRequest
                                   ):
        """
        职责：处理对话逻辑
        :param user_id:
        :param payload:
        :return:
        """
