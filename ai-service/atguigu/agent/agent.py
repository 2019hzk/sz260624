"""

创建Agent
agent=create_agent()
agent=llm+tools

"""

from langchain.agents import create_agent

from atguigu.agent.harness.middleware.scope import SkillScopeMiddleAware
from atguigu.agent.harness.run.context import AgentRunContext, AgentRunState
from atguigu.agent.harness.tools.catalog import TOOL_CATALOG
from atguigu.agent.llm.adapter import get_llm_client
from atguigu.agent.llm.output import AgentOutput
from atguigu.agent.llm.prompt import build_system_prompt


def create_ai_agent():
    return create_agent(  # type:ignore
        model=get_llm_client(),
        system_prompt=build_system_prompt(),
        tools=TOOL_CATALOG.get_agent_tools(),
        middleware=[SkillScopeMiddleAware()],
        response_format=AgentOutput,
        context_schema=AgentRunContext,  # 类型提示，不传入都没有关系
        state_schema=AgentRunState
    )