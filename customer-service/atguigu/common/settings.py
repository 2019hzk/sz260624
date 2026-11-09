from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    database_url: str = Field(
        "postgresql+psycopg://customer_service:customer_service@192.168.200.166:5432/customer_service",
        description="PgSQL数据库的地址")

    jwt_secret: str = Field("ecommerce-secret", description="jwt秘钥")

    jwt_algorithm: str = Field("HS256", description="jwt加密以及解密的算法")
    app_host: str = Field("0.0.0.0", description="服务的访问域名")
    api_port: int = Field("8000", description="服务的访问端口")
    cors_origins: list[str] = Field(
        ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
        description="服务端允许的源"
    )
    conversation_idle_timeout_minutes: int = Field(30, description="AI模式下会话的有效时间")
    message_merge_delay_ms: int = Field(30, description="AI模式下消息的防抖时间窗口阈值")

    internal_service_token: str = Field("customer-internal-token", description="服务内部访问令牌")

    ai_worker_poll_interval_ms: int = Field(100, description="Woker领取Turn时间")
    ai_timeout_seconds: int = Field(30, description="请求AI Service的http超时时间")
    ai_service_url: str = Field("http://127.0.0.1:8002", description="AI Service服务地址")
    ai_worker_max_attempts: int = Field(3, description="当前轮次重试AI Service调用次数")
    ai_worker_retry_delay_seconds: int = Field(2, description="重试延时")

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


@lru_cache  # key: 函数对象   value:函数的返回值,缓存配置实例对象
def get_settings():
    return Settings()


if __name__ == '__main__':
    settings = get_settings()
    print(settings.jwt_secret)
    print(id(settings))

    settings1 = get_settings()
    print(settings1.app_host)
    print(id(settings1))
