from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.app.models.models import Message, Conversation, RealtimeEvent


class RealtimeService:

    def __init__(self, session: AsyncSession):
        self._session = session

    def add_event(self,
                  message: Message,
                  conversation: Conversation,
                  *,
                  notify_user: bool = False,
                  notify_staff: bool = False
                  ):
        """
        职责：供需要发送事件的调用方调用
        :return:
        """

        # 1. 确定目标通道
        target_channels = []
        if notify_user:
            target_channels.append(conversation.user_id)
        if notify_staff:
            target_channels.append("staff")

        # 2. 构建事件通道的数据结构
        event_data = {
            "role": message.role,  # 前端展示渲染效果【区分：AI / 人工】
            "content": message.content,  # 前端展示的内容【消息】
            "conversation_mode": conversation.mode  # 前端展示右上角的徽章区域[AI客服、等待人工、人工服务中]  保证实时更新过程中，徽章的变换
        }

        # 3. 遍历通道
        for target_channel in target_channels:
            self._session.add(RealtimeEvent(target=target_channel, data=event_data))   # 不会利用event_data，客服端只是作为一次信号，调用刷新工单列表接口


