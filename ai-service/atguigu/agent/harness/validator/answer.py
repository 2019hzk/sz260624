"""

校验可信答案(ANSWER)

"""
import re
from re import findall

from atguigu.agent.harness.validator.validator import ValidateAgentOutError
from atguigu.app.models.models import AgentToolCall
from atguigu.common.utils import normalized_resource_id
# 捕获组(分组、单独在从组里面获取到)
# 非捕获组(分组、不会单独在从组里面获取到)

RESOURCE_ID_RE = re.compile(
    r"\b(?:ORDER|PRODUCT|AS)[_-][A-Z0-9_-]+\b",
    re.IGNORECASE,
)

NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:元|块|件|台|套|笔|单)")



STATUS_CODE_MAP = {
    "已支付": "paid",
    "待发货": "pending_shipment",
    "已发货": "shipped",
    "已完成": "completed",
    "已取消": "cancelled",
    "已退款": "refunded",
    "运输中": "in_transit",
    "已签收": "delivered",
    "待处理": "pending",
    "已通过": "approved",
    "处理中": "processing",
    "已拒绝": "rejected"
}

def validate_answer(reply_text: str,
                    successful_tool_calls: list[AgentToolCall]
                    ):
    """


    职责：校验Agent的回复内容
    参数者1：Agent的回复内容
    参数者2：成功调用的业务类型工具记录列表
    :return:
    """
    unsupported_facts = []
    # 1. 根据工具调用记录查找实时
    evidence_text, evidence_number = _collect_fact_evidence(successful_tool_calls)

    # 2. 从回复中利用正则查询提取resource_id以及量词对应的数值
    # 2.1 利用正则查询resource_id(PRODUCT_001/ORDER_001/AS_SALE_001)

    for raw_id in set(re.findall(RESOURCE_ID_RE, reply_text)):
        normalize_resource_id = normalized_resource_id(raw_id)
        if normalize_resource_id not in evidence_text:
            unsupported_facts.append(normalize_resource_id)

    # 2.2 利用正则查询量词("999.0"元 "3"比订单)
    for number_id in set(re.findall(NUMBER_RE, reply_text)):
        if float(number_id) not in evidence_number:
            unsupported_facts.append(number_id)

    # 2.3 订单状态、物流状态、售后单状态(in 映射表)

    for  label,code in STATUS_CODE_MAP.items():
        if (label in  reply_text or  code in reply_text) and code not in evidence_text:
            unsupported_facts.append(code)


    if    unsupported_facts:
        values = "、".join(unsupported_facts)
        raise ValidateAgentOutError(
            f"回复中的业务事实缺少工具支持：{values}，请仅根据工具返回结果回答"
        )




def _collect_fact_evidence(successful_tool_calls: list[AgentToolCall]) -> tuple[set[str], set[str]]:
    """
    职责：从调用成功的业务工具中查询 资源ID、数值、状态

    # 1. 从调用成功的业务工具中参数部分找
    # 2. 从调用成功的业务工具的result中的data
    :param successful_tool_calls:
    :return:

    """
    evidence_text = set()
    evidence_number = set()

    def collect(value: object):
        """
        职责：收集需要的信息
        :return:
        """
        if isinstance(value, dict):
            for v in value.values():
                collect(v)
        if isinstance(value, list):
            evidence_number.add(len(value))
            for item in value:
                collect(item)

        if isinstance(value, str):
            evidence_text.add(value)

        if isinstance(value, int | float):
            evidence_number.add(float(value))

    for stc in successful_tool_calls:
        # 1. 获取参数部分

        collect(stc.arguments)  # dict[str,Any]  值：str   数值：int / float

        # 2. 获取result中的data
        collect(stc.result['data'])  # dict[str,Any]  list[dict[str,Any]]   price:188

    #  返回收集到的数据
    return evidence_text, evidence_number
