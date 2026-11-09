from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.models.enums import HandoffStatus
from atguigu.app.models.models import Conversation, Handoff


class HandoffService:

    def __init__(self, session: AsyncSession):
        self._session = session

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
