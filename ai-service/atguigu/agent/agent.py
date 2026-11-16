"""

创建Agent
agent=create_agent()
agent=llm+tools

"""
from typing import NotRequired

from langchain.agents import create_agent
from langchain_core.callbacks import UsageMetadataCallbackHandler

from pydantic import BaseModel, Field

from atguigu.agent.harness.run.context import AgentRunContext, AgentRunState
from atguigu.agent.harness.tools.catalog import TOOL_CATALOG
from atguigu.agent.llm.adapter import get_llm_client
from atguigu.agent.llm.output import AgentOutput
from atguigu.agent.llm.prompt import build_system_prompt
from langchain.agents import AgentState


# def create_ai_agent():
#     return create_agent(  # type:ignore
#         model=get_llm_client(),
#         system_prompt=build_system_prompt(),
#         tools=TOOL_CATALOG.get_agent_tools(),
#         response_format=AgentOutput,
#         context_schema=AgentRunContext,  # 类型提示，不传入都没有关系
#         state_schema= AgentRunState
#     )
class User(BaseModel):
    name: str = Field(description="用户名字")
    age: str = Field(description="用户的年龄")


class UserState(AgentState):
    address: str


def create_ai_agent():
    return create_agent(  # type:ignore
        model=get_llm_client(),
        response_format=User,
        context_schema=AgentRunContext,  # 类型提示，不传入都没有关系
        state_schema=UserState
    )


if __name__ == '__main__':
    # structured_response
    agent = create_ai_agent()

    call_back = UsageMetadataCallbackHandler()
    state = agent.invoke(
        {"messages": "我的名字叫Tom,今年23岁"})

    print(state)
