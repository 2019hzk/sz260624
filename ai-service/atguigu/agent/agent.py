"""

创建Agent
agent=create_agent()
agent=llm+tools

"""
from langchain.agents import create_agent


from atguigu.agent.llm.adapter import get_llm_client


def create_ai_agent():
    return create_agent(
        model=get_llm_client()
    )
