from typing import Any

import httpx

from atguigu.common.settings import get_settings


class EcommerceClient:
    """使用当前客户身份访问 Ecommerce Service 接口。"""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.settings = get_settings()

    async def get_json(
            self,
            resource_path: str,
            query_params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """发送只读请求并返回 JSON 响应数据"""

        # 1. 构建请求接口地址
        request_url = f"{self.settings.ecommerce_base_url}{resource_path}"

        # 2. 构建请求头
        request_headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        # 3. 构建客户端
        async with httpx.AsyncClient(
                timeout=self.settings.ecommerce_timeout_seconds,
                trust_env=False
        ) as http_client:
            # 3.1 发送请求获取数据
            response = await http_client.get(
                request_url,
                headers=request_headers,
                params=query_params
            )
            response.raise_for_status()

            # 3.2 返回接口数据（字典对象）
            return response.json()
