from fastapi import APIRouter

router = APIRouter(tags=["测试最小交互方式的路由"])


#  IO/网络传输
#  1. 数据在交互的时候 一定不会是一个对象(依附内存 只要脱离内存，对象不存在) 而是字节流(字符串)
#  2. 异步方式操作IO/网络传输，因为对这两种资源的操作，cpu是空闲的,异步本质是压榨cpu
#  3. 序列化、反序列化
#  3.1 序列化：将对象【字典、列表、User...】转成字符串，目的： IO/网络传输
#  3.2 反序列化：将字符串转成对象【字典、列表、User...】 目的：方便业务操作
#  FastAPI:自动完成序列化和反序列化



@router.get("/hello")
async def hello():
    return {"success": "ok"}
