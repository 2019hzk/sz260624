import redis.asyncio as redis

redis_client = redis.Redis(host="192.168.200.166", port=6379, decode_responses=True)
