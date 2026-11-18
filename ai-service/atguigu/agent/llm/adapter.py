"""
适配：
qwen
deepseek
jev-(system one)   (llm)   deepseek-flash
"""

from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from typesafe_sdk import AsyncTypeSafeClient

from atguigu.common.settings import get_settings


def get_llm_client():
    settings = get_settings()

    enable_thinking = "enabled" if settings.llm_thinking_mode == "True" else "disabled"

    # 基础参数
    model_kwargs = {
        "model": settings.llm_model,
        "api_key": settings.llm_api_key,
        "base_url": settings.llm_base_url,
        "timeout": settings.llm_timeout_seconds
    }

    if settings.llm_provider == "deepseek":
        return ChatDeepSeek(
            **model_kwargs,
            extra_body={
                "thinking": {"type": enable_thinking}
            }
        )

    return ChatOpenAI(
        **model_kwargs,
        use_responses_api=False  # 防止走错 chat (endpoint)  response api(endpoint)
    )


def get_jev_client() -> AsyncTypeSafeClient:
    """获取 TypeSafe Jev 模型客户端实例"""
    settings = get_settings()
    return AsyncTypeSafeClient(
        api_key=settings.typesafe_api_key,
        base_url=settings.typesafe_base_url,
        model=settings.typesafe_model,
    )
