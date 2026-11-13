"""

创建Agent
agent=create_agent()
agent=llm+tools

"""
from langchain.agents import create_agent
from langchain_core.callbacks import UsageMetadataCallbackHandler

from atguigu.agent.harness.run.context import AgentRunContext
from atguigu.agent.llm.adapter import get_llm_client


def create_ai_agent():
    return create_agent(  # type:ignore
        model=get_llm_client(),
        context_schema=AgentRunContext  # 类型提示，不传入都没有关系
    )


if __name__ == '__main__':
    agent = create_ai_agent()

    call_back = UsageMetadataCallbackHandler()
    state = agent.invoke(
        {"messages": "最近AI应用开发面试环境如何？简单给我总结一下，我最近挺焦虑"},
        config={
            "callbacks": [call_back]
        })
    print(call_back.usage_metadata)
