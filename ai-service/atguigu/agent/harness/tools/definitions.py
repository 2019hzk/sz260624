from langchain_core.tools import tool
from langchain.tools import ToolRuntime
from typing import Annotated

from atguigu.agent.harness.run.context import AgentRunContext
from atguigu.agent.harness.tools.executor import tool_executor
from atguigu.common.utils import normalized_resource_id
from atguigu.infrastructure.client import EcommerceClient


@tool
async def search_products(
        query: Annotated[str, "商品名称、类别、规格或用户描述的购买需求"],
        runtime: ToolRuntime[AgentRunContext],
) -> str:
    """
    根据用户需求搜索当前在售商品。
    用户询问某类商品、商品名称，但没有明确商品编号时调用。
    返回匹配商品的名称、类别、价格、库存、状态、描述和规格。
    """

    # 1. 构建电商服务客户端
    ecommerce_client = EcommerceClient(runtime.context.access_token)

    # 2. 构建请求参数
    tool_arguments = {"query": query.strip()}

    # 3. 调用工具执行器，返回结果
    return tool_executor.execute_tool(
        runtime,
        "search_products",
        tool_arguments,
        operator=lambda: ecommerce_client.get_json("/products", query_params=tool_arguments))


@tool
async def get_product(
        product_id: Annotated[str, "用户明确提供商品编号或商品搜索结果返回的商品编号，例如 PRODUCT_001"],
        runtime: ToolRuntime[AgentRunContext]
) -> str:
    """
    查询一个商品的名称、价格、实时库存、销售状态、描述和规格。
    用户已经明确商品编号，并询问该商品的详情或库存信息时调用。
    """

    # 1. 构建电商服务客户端
    ecommerce_client = EcommerceClient(runtime.context.access_token)

    normalized_product_id = normalized_resource_id(product_id)

    # 2. 构建请求参数
    tool_arguments = {"product_id": normalized_product_id}

    # 3. 调用工具执行器，返回结果
    return tool_executor.execute_tool(
        runtime,
        "get_product",
        tool_arguments,
        operator=lambda: ecommerce_client.get_json(f"/products/{normalized_product_id}"))


@tool
async def list_orders(runtime: ToolRuntime[AgentRunContext]) -> str:
    """
    查询当前用户的订单列表。
    用户询问自己的订单但没有明确订单编号时调用。
    返回订单编号、状态、金额、创建时间和商品信息，只读取数据，不取消订单、退款或修改地址。
    """

    #  ecommerce_client.get_json("/orders")

    # 1. 构建电商服务客户端
    ecommerce_client = EcommerceClient(runtime.context.access_token)

    # 2. 调用工具执行器，返回结果
    return tool_executor.execute_tool(
        runtime,
        "list_orders",
        {},
        operator=lambda: ecommerce_client.get_json("/orders"))


@tool
async def get_order(
        order_id: Annotated[str, "用户明确提供订单编号或订单列表返回的订单编号，例如 ORDER_001"],
        runtime: ToolRuntime[AgentRunContext]
) -> str:
    """
    查询当前用户的一条订单详情。
    用户已经明确订单编号，并询问该订单的状态、金额、创建时间或商品信息时调用。
    只读取数据，不取消订单、退款或修改地址。
    """

    # ecommerce_client.get_json(f"/orders/{normalized_order_id}")

    # 1. 构建电商服务客户端
    ecommerce_client = EcommerceClient(runtime.context.access_token)

    normalized_order_id = normalized_resource_id(order_id)

    # 2. 构建请求参数
    tool_arguments = {"order_id": normalized_order_id}

    # 3. 调用工具执行器，返回结果
    return tool_executor.execute_tool(
        runtime,
        "get_order",
        tool_arguments,
        operator=lambda: ecommerce_client.get_json(f"/products/{normalized_order_id}"))


@tool
async def get_logistics(
        order_id: Annotated[str, "用户明确提供订单编号或订单列表返回的订单编号，例如 ORDER_001"],
        runtime: ToolRuntime[AgentRunContext]
) -> str:
    """
    查询一个订单的物流公司、运单号、状态和物流轨迹。
    用户已经明确订单编号，并询问该订单的配送进度或物流信息时调用。
    订单基础信息应使用 get_order 查询
    """
    # ecommerce_client.get_json(f"/orders/{normalized_order_id}/logistics")

    # 1. 构建电商服务客户端
    ecommerce_client = EcommerceClient(runtime.context.access_token)

    normalized_order_id = normalized_resource_id(order_id)

    # 2. 构建请求参数
    tool_arguments = {"order_id": normalized_order_id}

    # 3. 调用工具执行器，返回结果
    return tool_executor.execute_tool(
        runtime,
        "get_logistics",
        tool_arguments,
        operator=lambda: ecommerce_client.get_json(f"/orders/{normalized_order_id}/logistics"))


@tool
async def list_after_sales(
        runtime: ToolRuntime[AgentRunContext],
        order_id: Annotated[str | None, "可选的订单编号；提供后只查询该订单的售后记录"] = None
) -> str:
    """
    查询当前用户的售后申请记录。
    用户询问退款、退货或换货申请的处理进度时调用。
    已经明确订单编号时按订单查询，否则返回当前用户的全部售后记录。
    """
    # ecommerce_client.get_json("/after-sales", query_params=query_params)

    # 1. 构建电商服务客户端
    ecommerce_client = EcommerceClient(runtime.context.access_token)

    normalized_order_id = normalized_resource_id(order_id) if order_id is not None else None

    # 2. 构建请求参数
    query_params = {"order_id": normalized_order_id} if normalized_order_id is not None else None

    # 3. 调用工具执行器，返回结果
    return tool_executor.execute_tool(
        runtime,
        "get_logistics",
        query_params or {},
        operator=lambda: ecommerce_client.get_json("/after-sales", query_params=query_params))
