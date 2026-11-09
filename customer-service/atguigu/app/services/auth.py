import jwt
from fastapi import HTTPException, status

from atguigu.app.schemas import CurrentUser
from atguigu.common.settings import get_settings


def authorized_user(authorization: str | None, *roles: str) -> CurrentUser:
    """
    职责： 根据访问接口所带的认证信息以及接口需要的用户角色
    返回的是认证后的用户对象(用户ID 用户角色)
    :param authorization:
    :param roles:
    :return:
    """

    # 1. 校验是否携带了认证信息
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证失败")

    # 2. 获取令牌
    access_token = authorization.split(" ", 1)[1]

    # 3. 解密(根据令牌获取用户的信息)
    current_user = decode_access_token(access_token)

    # 4. 判断用户的角色是否是接口资源要求的角色
    if current_user.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")

    # 5. 返回用户信息
    return current_user


def decode_access_token(access_token: str) -> CurrentUser:
    """
    职责： 根据令牌解码载荷信息
    :param access_token:
    :return:
    """

    payload = jwt.decode(access_token, key=get_settings().jwt_secret, algorithms=[get_settings().jwt_algorithm])

    return CurrentUser.model_validate(payload)


def encode_access_token(user_id: str) -> str:
    current_user = CurrentUser(user_id=user_id)
    access_token = jwt.encode(current_user.model_dump(), key=get_settings().jwt_secret,
                              algorithms=[get_settings().jwt_algorithm])

    return access_token
