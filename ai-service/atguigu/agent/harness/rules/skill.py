from enum import StrEnum
from dataclasses import dataclass


class SkillCode(StrEnum):
    """定义 Agent 可以加载的技能编码。"""

    PRODUCT_SERVICE = "product_service"  # 唯一
    ORDER_SERVICE = "order_service"  # 唯一
    LOGISTICS_SERVICE = "logistics_service"  # 唯一
    AFTER_SALES_SERVICE = "after_sales_service"  # 唯一
    POLICY_SERVICE = "policy_service"  # 唯一


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    code: SkillCode
    description: str
    tools: list[str]
    guidance: list[str]




class SkillCatalog:

    def __init__(self, definitions: list[SkillDefinition]):
        self.skill_definitions = {definition.code: definition for definition in definitions}


    def   get_skill_definition(self,skill_code:SkillCode):
        return self.skill_definitions[skill_code]

    def  get_skill_index(self)->str:
        """
        职责：获取领域精简描述
        :return:
        """

        return "\n".join(
            f"{definition.code}: {definition.description}" for definition in self.skill_definitions.values())


SKILL_CATALOG = SkillCatalog(
    [
        SkillDefinition(
            code=SkillCode.PRODUCT_SERVICE,
            description="商品搜索、商品详情、规格、价格和实时库存",
            guidance=[
                "用户未提供商品编号时，先使用 search_products 按关键词搜索商品。",
                "已知商品编号并查询商品详情、价格、规格或实时库存时，使用 get_product。",
            ],
            tools=["search_products", "get_product"]
        ),
        SkillDefinition(
            code=SkillCode.ORDER_SERVICE,
            description="订单列表、订单详情、订单状态、金额及取消订单/修改地址页面跳转",
            guidance=[
                "用户未提供订单编号时，先使用 list_orders 查询订单列表。",
                "已知订单编号并查询状态、金额或商品明细时，使用 get_order。",
                "当用户要求取消订单、修改地址或打开订单页面时，必须先调用 get_order 确认订单，再生成对应的 page_action；仅查询订单信息时不生成 page_action。",
            ],
            tools=["list_orders", "get_order"]
        ),
        SkillDefinition(
            code=SkillCode.LOGISTICS_SERVICE,
            description="具体订单的发货状态、承运公司、运单号和物流轨迹",
            guidance=[
                "用户未提供订单编号时，先使用 list_orders 查询订单列表。",
                "查询具体订单的配送进度、快递公司、运单号和物流轨迹时，使用 get_logistics。",
            ],
            tools=["list_orders", "get_logistics"]
        ),
        SkillDefinition(
            code=SkillCode.POLICY_SERVICE,
            description="七天无理由退货及平台通用售后规则说明",
            guidance=[
                "用户询问平台退换货政策、退款规则或帮助说明时，使用 search_knowledge 查询知识库。",
                "知识库内容仅用于解释平台通用规则，不用于判断用户实际的售后申请进度。",
            ],
            tools=["search_knowledge"]
        ),
        SkillDefinition(
            code=SkillCode.AFTER_SALES_SERVICE,
            description="用户实际售后申请记录、处理进度及申请售后页面跳转",
            guidance=[
                "用户询问自己实际的退款、退货或换货进度时，使用 list_after_sales 查询售后记录。",
                "当用户要求申请售后或查看售后页面时，必须先调用 get_order 确认订单，再生成对应的 page_action。",
            ],
            tools=["get_order", "list_after_sales"]
        ),
    ]
)
