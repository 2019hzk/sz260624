from typing import Callable, Awaitable, override

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse

from atguigu.agent.harness.rules.skill import SKILL_CATALOG
from atguigu.agent.harness.run.context import AgentRunState, AgentRunContext
from atguigu.agent.llm.output import AgentOutput


class SkillScopeMiddleAware(AgentMiddleware[AgentRunState, AgentRunContext, AgentOutput]):
    """
    定义类：目标希望能够对工具做裁剪（根据领域裁剪）

    """

    async def awrap_model_call(
            self,
            request: ModelRequest[AgentRunContext],
            handler: Callable[[ModelRequest[AgentRunContext]], Awaitable[ModelResponse[AgentOutput]]],
    ) -> ModelResponse[AgentOutput]:
        """
        在该阶段（Agent调用LLM之前）程序员可以单独的做增强[修改 模型request中的内容、修改模型response响应的内容]
        职责：根据领域码找该领域工具
        :param request:
        :param handler:
        :return:
        """

        # 1. 获取领域码
        skill_code = request.state.get('skill_code')

        all_tool_name= ["load_skill"]

        if  skill_code is not None:
            # 2. 获取技能对象
            definition = SKILL_CATALOG.get_skill_definition(skill_code)
            all_tool_name.extend(definition.tools)   # 支持跨领域

        # 3. 该领域真正的工具对象
        allow_tools = [tool for tool in request.tools if tool.name in all_tool_name]

        # 4. 修改给模型请求的工具(换掉了)
        return await handler(request.override(tools=allow_tools,model_settings={"parallel_tool_calls": False}))
