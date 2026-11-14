from enum import StrEnum
from dataclasses import dataclass
from typing import Any


class ActionCode(StrEnum):
    """定义服务端允许生成的页面动作编码。"""

    BROWSE_ORDERS = "browse_orders"  # 打开订单列表页
    OPEN_ORDER_DETAIL = "open_order_detail"  # 打开订单详情页
    CANCEL_ORDER = "cancel_order"  # 取消订单页
    EDIT_ADDRESS = "edit_address"  # 修改地址页
    APPLY_AFTER_SALE = "apply_after_sale"  # 新增售后单页
    VIEW_AFTER_SALES = "view_after_sales"  # 打开订单售后详情页


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    action_code: ActionCode
    label: str
    description: str  # 给前端用，llm找action_code用
    path_template: str
    resource_type: str | None = None  # resource_id(订单 or 商品)

    def build_page(self, resource_id: str | None = None) -> dict[str, Any]:
        """
        职责：构建业务写操作需要的按钮信息
        :return:
        """
        return {
            "label": self.label,
            "description": self.description,
            "href": self.path_template.format(resource_id=resource_id)
        }


class ActionCatalog:

    def __init__(self, definitions: list[ActionDefinition]):
        self.definitions = {action_definition.action_code: action_definition for action_definition in definitions}

    def get_action_definition(self, action_code: ActionCode) -> ActionDefinition:
        """
        职责: 根据action_code找对象
        :param action_code:
        :return:
        """
        return self.definitions[action_code]

    def get_page_action_index(self) -> str:
        """
        职责：返回action的简介信息
        :return:
        """
        return "\n".join(
            f"{definition.action_code}: {definition.description}" for definition in self.definitions.values())


ACTION_CATALOG = ActionCatalog(
    [
        ActionDefinition(
            action_code=ActionCode.BROWSE_ORDERS,
            label="查看我的订单",
            description="进入我的订单列表",
            path_template="/me",

        ),
        ActionDefinition(
            action_code=ActionCode.OPEN_ORDER_DETAIL,
            label="查看订单详情",
            description="进入订单详情查看状态与可用操作",
            path_template="/me/orders/{resource_id}",  # /me/orders/ORDER_001
            resource_type="order"
        ),
        ActionDefinition(
            action_code=ActionCode.CANCEL_ORDER,
            label="前往取消订单",
            description="进入订单页面核对状态并确认取消",
            path_template="/me/orders/{resource_id}/cancel",
            resource_type="order"
        ),
        ActionDefinition(
            action_code=ActionCode.EDIT_ADDRESS,
            label="前往修改地址",
            description="进入订单页面修改收货地址",
            path_template="/me/orders/{resource_id}/address",
            resource_type="order"

        ),
        ActionDefinition(
            action_code=ActionCode.APPLY_AFTER_SALE,
            label="申请售后",
            description="进入订单页面填写售后申请",
            path_template="/me/orders/{resource_id}/after-sale",
            resource_type="order"
        ),
        ActionDefinition(
            action_code=ActionCode.VIEW_AFTER_SALES,
            label="查看售后进度",
            description="进入订单页面查看售后记录",
            path_template="/me/orders/{resource_id}?section=after-sales",
            resource_type="order"
        ),
    ]
)
