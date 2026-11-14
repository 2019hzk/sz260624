from datetime import UTC, datetime
from uuid import uuid4


def get_uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def get_utcnow() -> datetime:
    return datetime.now(UTC)




def  normalized_resource_id(resource_id:str)->str:
    """
     规范业务资源的ID编号（清洗空格、转大写、替换_）
    :param resource_id:
    :return:
    """
    # 商品ID(PRODUCT-001)  订单ID ORDER_001
    return  resource_id.strip().upper().replace("-","_")
