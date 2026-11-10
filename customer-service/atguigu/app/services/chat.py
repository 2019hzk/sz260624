from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from atguigu.app.models.enums import MessageRole, ConversationMode, TurnStatus
from atguigu.app.models.models import Message, Conversation, ConversationTurn
from atguigu.app.schemas import ChatMessageRequest
from atguigu.app.services.handoff import HandoffService
from atguigu.app.services.realtime import RealtimeService
from atguigu.common.settings import get_settings
from atguigu.common.utils import get_utcnow, get_uid


class ChatService:

    def __init__(self, session: AsyncSession):
        self._session = session
        self._settings = get_settings()
        self._realtime_service = RealtimeService(session)
        self._handoff_service = HandoffService(session)

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
        conversation = await self._create_or_get_conversation(user_id)  # 可能会阻塞

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
        stmt = (select(Conversation)
                .where(Conversation.user_id == user_id, Conversation.mode != ConversationMode.CLOSED)
                .with_for_update())

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

    async def finish_turn(self,
                          claimed_turn: ConversationTurn,
                          ai_result: dict[str, Any],
                          error: Exception):
        """
        职责： 结算轮次相关信息
        :param claimed_turn:
        :param ai_result:
        :param error:
        :return:
        """
        # 1. 查询当前轮次对应的会话
        conversation = await  self._session.scalar(
            select(Conversation).where(Conversation.id == claimed_turn.conversation_id).with_for_update())

        # 2. 校验(用户是否插话)
        if claimed_turn.snapshot_message_id != self._get_latest_user_message_id(str(conversation)):
            # 2.1 代表 用户进行了新的会话插入,只是修改轮次的状态 不会保存ai的回复结果
            claimed_turn.status = TurnStatus.SUPERSED  # 终态
            await self._session.commit()
            return

        # 3. 如果调用ai-service失败
        if error is not None:
            # 3.1 重试用完
            if claimed_turn.attempts > self._settings.ai_worker_max_attempts:
                claimed_turn.status = TurnStatus.FAILED  # 终态
                # 记录失败消息【对内】以及让前端看到重试失败消息内容【对外】)
                self._save_ai_reply({"kind": "error", "text": "AI Service调用失败,请您稍后继续重试!"},
                                    conversation)

            # 3.2 重试未用完
            else:
                # 重试逻辑
                claimed_turn.status = TurnStatus.COLLECTING  # 初始态
                claimed_turn.collect_until = get_utcnow() + timedelta(
                    seconds=self._settings.ai_worker_retry_delay_seconds)  # 更新时间(已经过期)【慢一些调用ai-service】

            await  self._session.commit()
            return

        # 4. 调用ai-service成功(保存ai_result) 保存到哪些表中 【messages、realtime_events】？ 根据回复类型处理各自逻辑

        # 4.1 修改轮次状态为完成
        claimed_turn.status = TurnStatus.COMPLETED

        # 4.2 回复类型转人工请求
        if ai_result['reply_type'] == "REQUEST_HANDOFF":
            # a) 转人工请求
            # 创建工单   # summary:面向客服的工单简短摘要[llm]
            self._handoff_service.create_handoff(conversation, summary=ai_result['summary'])
            # b) 修改会话模式
            conversation.mode = ConversationMode.QUEUED

        #  4.3 回复类型是正常的回答
        # 保存转人工请求的内容到messages表和realtime_events表中
        self._save_ai_reply(ai_result, conversation)

        await self._session.commit()

    async def claim_turn_and_build_payload(self) -> tuple[ConversationTurn, dict[str, Any], str] | None:
        """
        职责： 领取轮次且构建请求载荷
        :return:
        """

        # 1. 领取到满足条件的轮次(1.1 轮次状态：collecting 1.2 轮次的时间到期)

        # a) 定义待领取轮次的SQL语句
        stmt = select(ConversationTurn).where(
            ConversationTurn.status == TurnStatus.COLLECTING,
            ConversationTurn.collect_until <= get_utcnow()
        ).order_by(ConversationTurn.collect_until)

        # b) 查询SQL语句
        claimed_turn = await  self._session.scalar(stmt)

        # 2. 判断是否领取到
        # 2.1 没有领取到
        if claimed_turn is None:
            return None

        # 2.2 领取到（修改轮次信息）
        # a) 查询当前轮次的会话
        conversation = await self._session.scalar(
            select(Conversation).where(Conversation.id == claimed_turn.conversation_id).with_for_update())  # 可能会阻塞
        # b) 修改轮次状态
        claimed_turn.status = TurnStatus.RUNNING
        # c) 更新领取轮次的次数（后续利用：轮次的重试判定）
        claimed_turn.attempts += 1
        # d) 更新领取轮次的回话快照用户角色消息ID
        latest_user_message_id = await self._get_latest_user_message_id(str(conversation.id))
        # ①)校验插话是否发生 ②)确定轮次的消息下限
        claimed_turn.snapshot_message_id = latest_user_message_id  # 当前领取轮次这一时刻，该轮次会话对应用户最新消息的消息ID

        # 3. 构建调用ai-service请求载荷
        payload: dict[str, Any] = await self._build_request_payload(claimed_turn, conversation)

        # 4. 提交(必须在此处提交，不要放到外部with代码快一起提交)
        await self._session.commit()

        # 5. 返回领取到的轮次、请求载荷、用户ID
        return claimed_turn, payload, str(conversation.user_id)

    async def _get_latest_user_message_id(self, conversation_id: str) -> int:
        """
        职责：获取当前轮次对应会话的[最新]"用户角色"的消息ID
        :param conversation_id:
        :return:
        """

        # 1. 定义查询SQL语句
        stmt = select(func.max(Message.id)).where(
            Message.conversation_id == conversation_id,
            Message.role == MessageRole.USER
        )

        # 2. 查询SQL语句
        latest_user_message_id = await  self._session.scalar(stmt)

        return latest_user_message_id

    async def _build_request_payload(self,
                                     claimed_turn: ConversationTurn,
                                     conversation: Conversation) -> dict[str, Any]:
        """
        职责： 构建AI Service请求载荷
        构建1 当前轮次的消息
        构建2 当前会话的历史消息
        :param claimed_turn:
        :param conversation:
        :return:
        """

        # 1. 构建当前会话对应轮次的消息
        # 1.1 构建确定当前轮次上线的消息ID
        stmt = select(func.max(Message.id)).where(
            Message.conversation_id == conversation.id,
            Message.role != MessageRole.USER
        )

        # 1.2 查询SQL语句
        lasted_reply_message_id = await self._session.scalar(stmt) or 0

        current_turn_messages_stmt = select(Message).where(
            Message.conversation_id == conversation.id,
            Message.id > lasted_reply_message_id,
            Message.id <= claimed_turn.snapshot_message_id
        ).order_by(Message.id)

        current_turn_messages = (await self._session.scalars(current_turn_messages_stmt)).all()

        # 2. 构建当前会话的历史消息(裁剪30条消息)
        # 2.1 定义查询历史消息的SQL语句
        history_stmt = select(Message).where(
            Message.conversation_id == conversation.id,
            Message.id < current_turn_messages[0].id
        ).order_by(Message.id.desc()).limit(30)

        # 2.2 查询历史消息的SQL语句
        history_messages = reversed((await self._session.scalars(history_stmt)).all())

        # 3. 返回载荷数据
        return {
            "conversation_id": conversation.id,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                    "type": message.message_type
                }
                for message in current_turn_messages

            ],
            "history": [
                {
                    "role": history.role,
                    "content": history.content,
                    "type": history.message_type
                }
                for history in history_messages
            ]
        }

    def _save_ai_reply(self,
                       ai_result: dict[str, Any],
                       conversation: Conversation
                       ):
        """
        职责：保存回复内容到messages表和realtime_events表中
        :param ai_result:
        :return:
        """

        # 1. 保存回复内容到messages表（对内）
        message = Message(
            message_id=get_uid("msg"),
            conversation_id=conversation.id,
            role=MessageRole.AI,
            message_type="text",  # 回复类型只支持文本回复
            content=ai_result  # 直接将ai-result的字典结构的内容存到消息表的content中了。
        )

        self._session.add(message)

        # 2. 修改会话的最后一次有效时间
        conversation.last_active_at = get_utcnow()

        # 3. 保存回复内容到realtime_events表(对外)
        self._realtime_service.add_event(message, conversation,
                                         notify_user=True,
                                         notify_staff=conversation.mode == ConversationMode.QUEUED)
